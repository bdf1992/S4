"""Foundation 1 collector — walks skills/ and .claude/skills/, emits one
data point per project skill describing its harness-shim coverage status.

A "project skill" is a directory under skills/ that contains a SKILL.md.
Coverage is content-based: any .claude/skills/<any>/SKILL.md whose body
references `skills.<project_skill>` (the python module path) counts as a
shim that pre-runs that project skill's deterministic entry. Umbrella
shims like /verify and /activations therefore cover multiple project
skills with one file. Exemptions encode the "Not required for" rules in
.claude/skills/_PATTERN.md: leash-toggle skills auto-exempt by presence
of leash_state.json, plus a small STATIC_EXEMPT map for bespoke cases
(e.g. the meta-skill that builds other skills).

Run via:
  python -m tools.shim_coverage                # tabular report to stdout
  python -m tools.shim_coverage --jsonl        # data points as jsonl to stdout
  python -m tools.shim_coverage --strict       # exit 1 if any uncovered

See: foundations/data-point.md, foundations/collection-program.md,
.claude/skills/_PATTERN.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from boards.lib import data_point as dp

COLLECTOR_ID = "shim_coverage"
KIND = "shim_coverage_status"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["skill_name", "status", "shim_paths", "exempt_reason"],
    "properties": {
        "skill_name": {"type": "string"},
        "status": {"enum": ["covered", "missing", "exempt"]},
        "shim_paths": {"type": "array", "items": {"type": "string"}},
        "exempt_reason": {"type": ["string", "null"]},
    },
}
REPO = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO / "skills"
SHIMS_DIR = REPO / ".claude" / "skills"

STATIC_EXEMPT = {
    "subprotocol-for-claude-code": "meta-skill (builds other skills)",
}
LEASH_TOGGLE_REASON = "leash-toggle skill, not measurement"


def _exempt_reason(skill_name: str) -> str | None:
    """Return the exemption reason for a skill, or None if non-exempt.
    Leash-toggle skills are detected by the presence of leash_state.json
    (the toggle's persisted state) — derived rather than listed so a new
    leash sibling does not require editing this file."""
    if skill_name in STATIC_EXEMPT:
        return STATIC_EXEMPT[skill_name]
    if (SKILLS_DIR / skill_name / "leash_state.json").exists():
        return LEASH_TOGGLE_REASON
    return None


def _project_skills() -> list[str]:
    if not SKILLS_DIR.exists():
        return []
    out = []
    for child in sorted(SKILLS_DIR.iterdir()):
        if child.is_dir() and (child / "SKILL.md").exists():
            out.append(child.name)
    return out


def _all_shims() -> list[Path]:
    if not SHIMS_DIR.exists():
        return []
    return sorted(SHIMS_DIR.glob("*/SKILL.md"))


def _frontmatter_covers(content: str) -> list[str]:
    """Extract the `covers:` list from a shim's YAML frontmatter, if any.
    Supports flow-style: `covers: [a, b, c]`. Block-style not supported
    (deliberate — keep the surface small)."""
    if not content.startswith("---"):
        return []
    end = content.find("\n---", 3)
    if end < 0:
        return []
    fm = content[3:end]
    m = re.search(r"^covers:\s*\[([^\]]*)\]\s*$", fm, re.MULTILINE)
    if not m:
        return []
    items = [x.strip().strip("\"'") for x in m.group(1).split(",")]
    return [x for x in items if x]


def _shims_referencing(skill_name: str) -> list[str]:
    """Return relpaths of shims that cover this project skill — either by
    referencing `skills.<name>` in their body, or by declaring the name in
    a `covers:` frontmatter list (umbrella shims like /verify)."""
    pattern = re.compile(rf"\bskills\.{re.escape(skill_name)}\b")
    out: list[str] = []
    for shim_md in _all_shims():
        try:
            content = shim_md.read_text(encoding="utf-8")
        except OSError:
            continue
        if pattern.search(content) or skill_name in _frontmatter_covers(content):
            out.append(str(shim_md.relative_to(REPO)).replace("\\", "/"))
    return sorted(out)


def compute_source_state() -> str:
    h = hashlib.sha256()
    for skill in _project_skills():
        h.update(skill.encode()); h.update(b"\0")
        skill_md = SKILLS_DIR / skill / "SKILL.md"
        h.update(hashlib.sha256(skill_md.read_bytes()).digest())
    for shim_md in _all_shims():
        rel = str(shim_md.relative_to(REPO)).replace("\\", "/")
        h.update(rel.encode()); h.update(b"\0")
        h.update(hashlib.sha256(shim_md.read_bytes()).digest())
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


def _status_for(skill_name: str) -> dict:
    reason = _exempt_reason(skill_name)
    if reason is not None:
        return {
            "skill_name": skill_name,
            "status": "exempt",
            "shim_paths": [],
            "exempt_reason": reason,
        }
    shims = _shims_referencing(skill_name)
    if shims:
        return {
            "skill_name": skill_name,
            "status": "covered",
            "shim_paths": shims,
            "exempt_reason": None,
        }
    return {
        "skill_name": skill_name,
        "status": "missing",
        "shim_paths": [],
        "exempt_reason": None,
    }


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    out: list[dict] = []
    for skill in _project_skills():
        value = _status_for(skill)
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID,
            kind=KIND,
            value=value,
            source_state=source_state,
            collector_pointer=cp,
        ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    name = data_point["value"]["skill_name"]
    if not (SKILLS_DIR / name / "SKILL.md").exists():
        return "dangling", "project_skill_removed"
    current = _status_for(name)
    if current == data_point["value"]:
        return "live", "match"
    return "dangling", f"status_drift:{data_point['value']['status']}->{current['status']}"


def _render_table(points: list[dict]) -> str:
    lines = [
        "# Shim coverage — project skills under `skills/` vs `.claude/skills/<name>/SKILL.md`",
        "",
        "| Skill | Status | Shim / Exempt reason |",
        "| --- | --- | --- |",
    ]
    counts = {"covered": 0, "missing": 0, "exempt": 0}
    for p in points:
        v = p["value"]
        counts[v["status"]] += 1
        if v["status"] == "covered":
            third = ", ".join(f"[{s}]({s})" for s in v["shim_paths"])
        elif v["status"] == "exempt":
            third = f"_exempt — {v['exempt_reason']}_"
        else:
            third = (
                "_missing — add a shim under `.claude/skills/` whose body "
                "references `skills." + v["skill_name"] + "` per "
                "[_PATTERN.md](.claude/skills/_PATTERN.md)_"
            )
        lines.append(f"| `{v['skill_name']}` | **{v['status']}** | {third} |")
    lines += [
        "",
        f"Totals: covered = {counts['covered']}, exempt = {counts['exempt']}, missing = {counts['missing']}",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", action="store_true",
                    help="emit data points as jsonl instead of a table")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any project skill is uncovered")
    args = ap.parse_args()

    source_state = compute_source_state()
    points = collect(source_state)

    if args.jsonl:
        for p in points:
            sys.stdout.write(json.dumps(p, sort_keys=True) + "\n")
    else:
        print(_render_table(points))
        print(f"\nsource_state: {source_state}")

    if args.strict:
        for p in points:
            if p["value"]["status"] == "missing":
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
