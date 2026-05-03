"""Foundation 1 collector — measures peer consumption of skills.

The diagnosis behind this collector: skills under skills/ are produced
under 0.1+0.2+0.3 discipline but rarely *consumed* by other skills,
tools, or shims. The "floor compounds because peers consume it" property
in CLAUDE.md cannot be measured without an explicit lateral metric.
This is that metric.

Per skill, walks every .py file outside that skill's own tree under:

  - skills/<other>/      (peer skills)
  - tools/               (top-level tools and integrations)
  - boards/              (board subsystem)
  - .claude/skills/      (Claude Code shim layer)

For each file, AST-parses the imports. If the file references
`skills.<this_skill>` or `from skills.<this_skill>...` in any form,
it counts as a peer consumer. Submodule resolution (lib, signals,
collectors, orchestrate) is preserved so the report can distinguish
"someone imports the lib" from "someone imports the runtime signal."

Run via:
  python -m tools.floor_growth                 # human-readable table + ranked targets
  python -m tools.floor_growth --jsonl         # data points to stdout
  python -m tools.floor_growth --ranked        # ranked next-target candidates only
  python -m tools.floor_growth --strict        # exit 1 if any skill is isolated

Note on D-001: this tool itself imports `boards.lib.data_point`, which
is a vendor-copied module — the very pattern this collector helps
surface. The collector does not pretend to fix the underlying lib
duplication; it measures the absence of *consumer* edges, of which
shared-lib refactoring is one downstream resolution.

See: foundations/data-point.md, foundations/collection-program.md.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

from boards.lib import data_point as dp

COLLECTOR_ID = "floor_growth"
KIND = "skill_peer_consumption"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["skill_name", "status", "peer_importers",
                 "lib_consumed", "signals_consumed",
                 "collectors_consumed", "verifier_present"],
    "properties": {
        "skill_name": {"type": "string"},
        "status": {"enum": ["graduated", "candidate", "isolated", "no_structure"]},
        "peer_importers": {"type": "array",
                           "items": {"type": "object",
                                     "required": ["importer", "submodule"]}},
        "lib_consumed": {"type": "boolean"},
        "signals_consumed": {"type": "boolean"},
        "collectors_consumed": {"type": "boolean"},
        "verifier_present": {"type": "boolean"},
    },
}
INPUTS = ["skills/*/SKILL.md", "skills/*/verify.py",
          "skills/**/*.py", "tools/*.py", "boards/**/*.py",
          ".claude/skills/**/*.py"]

REPO = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO / "skills"


def _project_skills() -> list[str]:
    if not SKILLS_DIR.exists():
        return []
    return sorted(c.name for c in SKILLS_DIR.iterdir()
                  if c.is_dir() and (c / "SKILL.md").is_file())


def _scan_dirs() -> list[Path]:
    """Directories whose .py files we treat as candidate consumers."""
    out = [REPO / "tools", REPO / "boards", REPO / ".claude" / "skills"]
    if SKILLS_DIR.exists():
        out.extend(d for d in SKILLS_DIR.iterdir() if d.is_dir())
    return [d for d in out if d.exists()]


def _all_py_files() -> list[Path]:
    files: list[Path] = []
    for root in _scan_dirs():
        files.extend(p for p in root.rglob("*.py")
                     if "__pycache__" not in p.parts)
    return sorted(set(files))


def _imports_in(file_path: Path) -> list[tuple[str, str | None]]:
    """Returns list of (top_skill_name, submodule_path) for each
    `skills.<name>...` import found in the file. submodule_path is
    `lib`, `signals`, `collectors`, `orchestrate`, etc., or None for
    a bare `import skills.<name>`."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError, UnicodeDecodeError):
        return []
    out: list[tuple[str, str | None]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            parts = mod.split(".")
            if len(parts) >= 2 and parts[0] == "skills":
                sub = parts[2] if len(parts) >= 3 else None
                out.append((parts[1], sub))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if len(parts) >= 2 and parts[0] == "skills":
                    sub = parts[2] if len(parts) >= 3 else None
                    out.append((parts[1], sub))
    return out


def _file_inside_skill(file_path: Path, skill_name: str) -> bool:
    skill_root = SKILLS_DIR / skill_name
    try:
        file_path.relative_to(skill_root)
        return True
    except ValueError:
        return False


def _peer_consumption_map() -> dict[str, list[dict]]:
    """skill_name -> list of {importer: relpath, submodule: str|None}."""
    out: dict[str, list[dict]] = {s: [] for s in _project_skills()}
    for f in _all_py_files():
        rel = f.relative_to(REPO).as_posix()
        for skill, sub in _imports_in(f):
            if skill not in out:
                continue
            if _file_inside_skill(f, skill):
                continue  # self-import doesn't count as peer consumption
            out[skill].append({"importer": rel, "submodule": sub})
    for s in out:
        out[s].sort(key=lambda d: (d["importer"], d["submodule"] or ""))
    return out


def _verifier_present(skill_name: str) -> bool:
    return (SKILLS_DIR / skill_name / "verify.py").is_file()


def _has_subdir(skill_name: str, sub: str) -> bool:
    return (SKILLS_DIR / skill_name / sub).is_dir()


def _classify(verifier: bool, importers: list[dict],
              has_signals: bool) -> str:
    """Rung-status estimate, conservatively. See CLAUDE.md §"four-rung
    graduation": 3.0-graduated requires peer 3.0 *uses* it. We treat
    any external-file import as peer-use evidence, which is generous
    (an import is not always a runtime call), but the converse — no
    import at all — is a strong negative signal."""
    if not verifier:
        return "no_structure"
    if not importers:
        return "isolated"
    # Verifier present + at least one peer importer — call it candidate.
    # Reserve "graduated" for the additional condition that a runtime
    # signal is consulted (the 0.2 → 0.3 wiring), since that is the
    # named bottleneck in the current diagnosis.
    if has_signals and any(i["submodule"] == "signals" for i in importers):
        return "graduated"
    return "candidate"


def _status_for(skill_name: str, importers: list[dict]) -> dict:
    verifier = _verifier_present(skill_name)
    has_signals = _has_subdir(skill_name, "signals")
    submods = {i["submodule"] for i in importers}
    return {
        "skill_name": skill_name,
        "status": _classify(verifier, importers, has_signals),
        "peer_importers": importers,
        "lib_consumed": "lib" in submods,
        "signals_consumed": "signals" in submods,
        "collectors_consumed": "collectors" in submods,
        "verifier_present": verifier,
    }


def compute_source_state() -> str:
    h = hashlib.sha256()
    for skill in _project_skills():
        h.update(skill.encode()); h.update(b"\0")
        h.update(b"v" if _verifier_present(skill) else b"-")
    for f in _all_py_files():
        rel = f.relative_to(REPO).as_posix()
        h.update(rel.encode()); h.update(b"\0")
        h.update(hashlib.sha256(f.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32]


def _collector_pointer() -> dict:
    return {
        "kind": "collector",
        "target": {"collector_id": COLLECTOR_ID},
        "resolver": "collector_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved",
        "last_payload": None,
        "last_reason": None,
    }


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    consumption = _peer_consumption_map()
    out: list[dict] = []
    for skill in _project_skills():
        value = _status_for(skill, consumption[skill])
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND,
            value=value, source_state=source_state,
            collector_pointer=cp,
        ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    name = data_point["value"]["skill_name"]
    if not (SKILLS_DIR / name / "SKILL.md").is_file():
        return "dangling", "skill_removed"
    consumption = _peer_consumption_map()
    current = _status_for(name, consumption.get(name, []))
    if current == data_point["value"]:
        return "live", "match"
    return "dangling", f"status_drift:{data_point['value']['status']}->{current['status']}"


# ---- ranking ---------------------------------------------------------

# Leverage scoring. The diagnosis named two highest-value moves:
# (a) a peer skill that imports an existing isolated skill's lib/signals
# (b) wiring an existing 0.2 signal into an existing 0.3 at runtime.
# Skills with full 0.1+0.2 structure (verifier + signals/) but zero
# peer importers are the (a) targets. Skills with peer importers but no
# signals_consumed=True are the (b) targets.
LEVERAGE_RULES = [
    ("isolated_with_signals",
     "Built bottom-up (verifier + signals), zero peer importers. "
     "Highest leverage: write a peer skill that imports its lib or signals.",
     lambda v: v["status"] == "isolated" and (SKILLS_DIR / v["skill_name"] / "signals").is_dir()),
    ("isolated_no_signals",
     "Built bottom-up (verifier present), zero peer importers. "
     "Lower leverage than signal-bearing isolates but still floor-flat.",
     lambda v: v["status"] == "isolated" and not (SKILLS_DIR / v["skill_name"] / "signals").is_dir()),
    ("candidate_signal_unfenced",
     "Has peer importers but no peer consumes its signals/. "
     "0.2 work exists; runtime fence missing. Wire it in.",
     lambda v: v["status"] == "candidate" and (SKILLS_DIR / v["skill_name"] / "signals").is_dir()
              and not v["signals_consumed"]),
    ("no_structure",
     "Missing verifier — sub-1.0. Resolve via skill_without_verifier proposals.",
     lambda v: v["status"] == "no_structure"),
]


def _ranked(points: list[dict]) -> list[tuple[str, str, list[str]]]:
    """Returns [(rule_id, rule_text, [skill_names])] in priority order."""
    out: list[tuple[str, str, list[str]]] = []
    used: set[str] = set()
    for rule_id, rule_text, pred in LEVERAGE_RULES:
        bucket = []
        for p in points:
            v = p["value"]
            if v["skill_name"] in used:
                continue
            if pred(v):
                bucket.append(v["skill_name"])
                used.add(v["skill_name"])
        if bucket:
            out.append((rule_id, rule_text, sorted(bucket)))
    return out


# ---- rendering -------------------------------------------------------

def _render_table(points: list[dict]) -> str:
    lines = [
        "# Floor growth — peer consumption of project skills",
        "",
        "| Skill | Status | Verifier | Lib used | Signals used | Importers |",
        "| --- | --- | :-: | :-: | :-: | --- |",
    ]
    counts = {"graduated": 0, "candidate": 0, "isolated": 0, "no_structure": 0}
    for p in points:
        v = p["value"]
        counts[v["status"]] += 1
        importers = v["peer_importers"]
        if importers:
            shown = ", ".join(
                f"[{i['importer']}]({i['importer']})" + (f"·{i['submodule']}" if i['submodule'] else "")
                for i in importers[:4]
            )
            if len(importers) > 4:
                shown += f" +{len(importers) - 4}"
        else:
            shown = "_none_"
        lines.append(
            f"| `{v['skill_name']}` | **{v['status']}** | "
            f"{'yes' if v['verifier_present'] else 'no'} | "
            f"{'yes' if v['lib_consumed'] else 'no'} | "
            f"{'yes' if v['signals_consumed'] else 'no'} | "
            f"{shown} |"
        )
    lines += [
        "",
        f"Totals: graduated = {counts['graduated']}, "
        f"candidate = {counts['candidate']}, "
        f"isolated = {counts['isolated']}, "
        f"no_structure = {counts['no_structure']}",
    ]
    return "\n".join(lines)


def _render_ranked(points: list[dict]) -> str:
    ranked = _ranked(points)
    if not ranked:
        return "# Floor growth — ranked targets\n\n_No floor-growth candidates surfaced. The floor is either fully consumed or fully empty._"
    lines = ["# Floor growth — ranked next-target candidates", ""]
    for rule_id, rule_text, names in ranked:
        lines.append(f"## {rule_id}")
        lines.append("")
        lines.append(rule_text)
        lines.append("")
        for n in names:
            lines.append(f"- `{n}`")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", action="store_true",
                    help="emit data points as jsonl instead of a table")
    ap.add_argument("--ranked", action="store_true",
                    help="emit ranked next-target candidates only")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any skill is isolated")
    args = ap.parse_args()

    source_state = compute_source_state()
    points = collect(source_state)

    if args.jsonl:
        for p in points:
            sys.stdout.write(json.dumps(p, sort_keys=True) + "\n")
    elif args.ranked:
        print(_render_ranked(points))
    else:
        print(_render_table(points))
        print()
        print(_render_ranked(points))
        print(f"\nsource_state: {source_state}")

    if args.strict:
        for p in points:
            if p["value"]["status"] == "isolated":
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
