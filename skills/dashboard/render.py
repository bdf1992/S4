"""Dashboard render: compose every existing artifact into one operator-facing markdown.

Pure 0.1 deterministic render over live source. No new collector, no persisted
snapshot. Reads:

  - foundations/{data-point,collection-program,pointer,zero-four,grading-events}.md
  - debts/D-*.json (via boards.adapters)
  - foundations/grading-events.md (via boards.adapters.grading_events)
  - skills/leash_*/exemplars/{proposed,promoted}/ (via boards.adapters.exemplars)
  - skills/leash_*/leash_state.json
  - skills/regime_audit/outputs/run-*/stats.json (history for trend)

Usage:
  python -m skills.dashboard.render
  python -m skills.dashboard.render --no-trend
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from boards.adapters import all_boards, exemplars, grading_events  # noqa: E402
from skills.dashboard import snapshot as _snap  # noqa: E402

BEDROCK_FILES = [
    ("data-point", "foundations/data-point.md"),
    ("collection-program", "foundations/collection-program.md"),
    ("pointer", "foundations/pointer.md"),
    ("zero-four", "foundations/zero-four.md"),
    ("grading-events", "foundations/grading-events.md"),
]


def _today() -> _dt.date:
    return _dt.date.today()


def _mtime_iso(path: Path) -> str:
    if not path.exists():
        return "(missing)"
    return _dt.date.fromtimestamp(path.stat().st_mtime).isoformat()


def _age_days(date_str: str) -> int | None:
    try:
        d = _dt.date.fromisoformat(date_str)
    except (TypeError, ValueError):
        return None
    return (_today() - d).days


def _link(rel_path: str, label: str | None = None) -> str:
    label = label or rel_path
    return f"[{label}]({rel_path})"


def _section(title: str) -> list[str]:
    return ["", f"## {title}", ""]


def _pending_decisions_section() -> list[str]:
    out = _section(f"Awaiting your decision")
    pending = _snap._pending_decisions()
    if not pending:
        out.append("_No proposals waiting on the operator._")
        return out
    now_iso = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    out.append(f"**{len(pending)} proposal(s)** with `proposal.json` at `status: proposed`, "
               f"not yet signed in {_link('approvals/decisions.jsonl')}.")
    out.append("")
    for p in pending:
        pid = p["proposal_id"]
        target = p.get("target_skill_path") or "?"
        pre = p.get("pre_verification") or {}
        passed = pre.get("checks_passed", 0)
        total = pre.get("checks_total", 0)
        budget = pre.get("audit_budget") or "?/?"
        overall = pre.get("overall") or "?"
        gap = p.get("gap_narrative") or ""
        out.append(f"### `{pid}`")
        out.append("")
        out.append(f"- **Target:** {_link(target) if target != '?' else target}")
        out.append(f"- **Pre-verification:** `{overall}` · {passed}/{total} checks · audit budget {budget}")
        out.append(f"- **Gap:** {gap}")
        out.append("")
        out.append("Promote — edit `<you>` to your name, paste in a terminal:")
        out.append("")
        out.append("```bash")
        out.append("mkdir -p approvals")
        out.append("cat >> approvals/decisions.jsonl <<'JSON'")
        out.append(f'{{"proposal_id":"{pid}","verdict":"promote","decided_at":"{now_iso}","by":"<you>"}}')
        out.append("JSON")
        out.append(f"python -m tools.promote {pid} --dry-run")
        out.append(f"python -m tools.promote {pid}")
        out.append("```")
        out.append("")
        out.append("<details><summary>Reject instead?</summary>")
        out.append("")
        out.append("```bash")
        out.append("mkdir -p approvals")
        out.append("cat >> approvals/decisions.jsonl <<'JSON'")
        out.append(f'{{"proposal_id":"{pid}","verdict":"reject","decided_at":"{now_iso}","by":"<you>","reason":"<reason>"}}')
        out.append("JSON")
        out.append("```")
        out.append("")
        out.append("</details>")
        out.append("")
    return out


def _bedrock_section() -> list[str]:
    out = _section("Bedrock primitives")
    out.append("| Spec | Source | Last modified |")
    out.append("| --- | --- | --- |")
    for name, rel in BEDROCK_FILES:
        p = REPO / rel
        mark = "OK" if p.exists() else "MISSING"
        mt = _mtime_iso(p)
        out.append(f"| {name} | {_link(rel)} | {mt} ({mark}) |")
    return out


def _audit_bundle_history() -> list[tuple[Path, dict]]:
    bundles_dir = REPO / "skills" / "regime_audit" / "outputs"
    if not bundles_dir.is_dir():
        return []
    rows: list[tuple[Path, dict]] = []
    for run_dir in sorted(bundles_dir.glob("run-*"), key=lambda p: p.stat().st_mtime):
        stats_path = run_dir / "stats.json"
        if not stats_path.exists():
            continue
        try:
            data = json.loads(stats_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        rows.append((run_dir, data))
    return rows


def _floor_ratio_section(*, include_trend: bool) -> list[str]:
    out = _section("Floor ratio")
    history = _audit_bundle_history()
    if not history:
        out.append("_No audit bundles found. Run `python -m skills.regime_audit.orchestrate` to emit one._")
        return out
    latest_dir, latest_data = history[-1]
    stats = latest_data.get("stats", {})
    fr = stats.get("floor_ratio")
    by_regime = stats.get("by_regime", {})
    rel_latest = latest_dir.relative_to(REPO).as_posix()
    fr_str = f"{fr:.3f}" if isinstance(fr, (int, float)) else str(fr)
    out.append(f"**Latest floor_ratio = {fr_str}**  (source: {_link(rel_latest + '/stats.json')})")
    out.append("")
    out.append("Definition: `(0.1 + 0.2) / 0.3` — the substrate-to-free-write ratio. Growing means the floor is compounding.")
    out.append("")
    out.append("| Regime | Count |")
    out.append("| --- | --- |")
    regime_order = ["bedrock", "0.0", "0.1", "0.2", "0.3", "unclassified"]
    for r in regime_order:
        if r in by_regime:
            out.append(f"| {r} | {by_regime[r]} |")
    leftover = [r for r in by_regime if r not in regime_order]
    for r in sorted(leftover):
        out.append(f"| {r} | {by_regime[r]} |")

    if include_trend and len(history) > 1:
        out.append("")
        out.append("### Trend across audit bundles")
        out.append("")
        out.append("| When | Bundle | floor_ratio | 0.1 | 0.2 | 0.3 |")
        out.append("| --- | --- | --- | --- | --- | --- |")
        for d, data in history:
            s = data.get("stats", {})
            ts = _dt.datetime.fromtimestamp(d.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            fr_v = s.get("floor_ratio")
            fr_render = f"{fr_v:.3f}" if isinstance(fr_v, (int, float)) else str(fr_v)
            br = s.get("by_regime", {})
            rel = d.relative_to(REPO).as_posix()
            out.append(
                f"| {ts} | {_link(rel, d.name)} | {fr_render} | "
                f"{br.get('0.1','-')} | {br.get('0.2','-')} | {br.get('0.3','-')} |"
            )
        first = history[0][1].get("stats", {}).get("floor_ratio")
        last = history[-1][1].get("stats", {}).get("floor_ratio")
        if isinstance(first, (int, float)) and isinstance(last, (int, float)):
            delta = last - first
            arrow = "growing" if delta > 0 else ("flat" if delta == 0 else "shrinking")
            out.append("")
            out.append(f"**Δ across {len(history)} runs:** {first:.3f} → {last:.3f} ({arrow}, {delta:+.3f}).")
    return out


def _boards_section() -> list[str]:
    out = _section("Boards")
    cards = all_boards.cards()
    if not cards:
        out.append("_No board cards found._")
        return out
    out.append("| Board | Status | Total | Open | Load-bearing-open | Last activity | Source |")
    out.append("| --- | --- | --- | --- | --- | --- | --- |")
    for c in cards:
        src = c.get("source_label") or ""
        # Source labels can be a single path ("debts/"), a glob ("skills/leash_*/exemplars/"),
        # or a multi-area description ("skills/gap_audit/ + proposals/ + approvals/"). Only
        # the first form is a clickable link; the others render as plain text so we don't
        # ship a malformed [label](broken-href) into the operator's reading surface.
        src_link = _link(src) if src and " " not in src and "+" not in src else src
        last_activity = c.get("last_updated_at") or "-"
        out.append(
            f"| {c['id']} | {c['status']} | {c['total']} | {c['open']} | "
            f"{c['load_bearing_open']} | {last_activity} | {src_link} |"
        )
    out.append("")
    leaf_names = ", ".join(f"`{n}`" for n, _, _ in all_boards.SUB_BOARDS)
    out.append(f"_Drill in: `python -m boards <name>` — names: {leaf_names}._")
    return out


def _leash_section() -> list[str]:
    out = _section("Leashes")
    rows: list[dict] = []
    for leash_dir in sorted(REPO.glob("skills/leash_*")):
        state_path = leash_dir / "leash_state.json"
        state = "(missing)"
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8")).get("state", "?")
            except json.JSONDecodeError:
                state = "(parse-error)"
        proposed = list((leash_dir / "exemplars" / "proposed").glob("*.json")) \
            if (leash_dir / "exemplars" / "proposed").is_dir() else []
        promoted = list((leash_dir / "exemplars" / "promoted").glob("*.json")) \
            if (leash_dir / "exemplars" / "promoted").is_dir() else []
        outputs = list(leash_dir.glob("outputs/run-*")) \
            if (leash_dir / "outputs").is_dir() else []
        rows.append({
            "name": leash_dir.name,
            "state": state,
            "proposed": len(proposed),
            "promoted": len(promoted),
            "outputs": len(outputs),
            "rel": leash_dir.relative_to(REPO).as_posix(),
        })
    if not rows:
        out.append("_No leash skills found._")
        return out
    out.append("| Leash | Toggle | Proposed | Promoted | Output bundles | Source |")
    out.append("| --- | --- | --- | --- | --- | --- |")
    for r in rows:
        out.append(
            f"| {r['name']} | **{r['state']}** | {r['proposed']} | {r['promoted']} | "
            f"{r['outputs']} | {_link(r['rel'] + '/SKILL.md')} |"
        )
    return out


def _skills_regime_section() -> list[str]:
    out = _section("Skills — regime distribution")
    history = _audit_bundle_history()
    if not history:
        out.append("_No audit bundles to source from._")
        return out
    _, latest_data = history[-1]
    by_skill: dict[str, dict[str, int]] = latest_data.get("stats", {}).get("by_skill", {})
    if not by_skill:
        out.append("_Latest audit bundle has no by_skill data._")
        return out
    regime_cols = ["bedrock", "0.0", "0.1", "0.2", "0.3", "unclassified"]
    out.append("| Skill | " + " | ".join(regime_cols) + " | Total |")
    out.append("| --- " + "| --- " * (len(regime_cols) + 1) + "|")
    for skill in sorted(by_skill):
        counts = by_skill[skill]
        cells = [str(counts.get(r, 0)) for r in regime_cols]
        total = sum(counts.values())
        out.append(f"| {skill} | " + " | ".join(cells) + f" | {total} |")
    return out


def _header() -> list[str]:
    today = _today().isoformat()
    return [
        f"# zero-four-experiment — operator dashboard",
        "",
        f"_Rendered {today}. Pure read-only view; no source modified._",
        "",
        f"Highest abstraction: {_link('CLAUDE.md')}. Drill in via the per-board commands listed below.",
    ]


def render_dashboard(*, include_trend: bool = True) -> str:
    parts: list[str] = []
    parts.extend(_header())
    parts.extend(_pending_decisions_section())
    parts.extend(_bedrock_section())
    parts.extend(_floor_ratio_section(include_trend=include_trend))
    parts.extend(_boards_section())
    parts.extend(_leash_section())
    parts.extend(_skills_regime_section())
    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    include_trend = "--no-trend" not in sys.argv[1:]
    print(render_dashboard(include_trend=include_trend))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
