"""Render a directory of JSON records as a kanban board.

Group cards by `status` (column axis); optionally split into lanes by
`severity`. Cards show id, subject, payoff teaser, age in days, and
depends_on / blocks edges if present. Supports declared column enum via
--columns so empty columns still appear.

Usage:
  python -m boards.render <source_dir>
  python -m boards.render <source_dir> --columns open,parked,closed_paid,closed_written_off,superseded
  python -m boards.render <source_dir> --no-lanes
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _today() -> _dt.date:
    return _dt.date.today()


def _age_days(date_str: str) -> int | None:
    try:
        d = _dt.date.fromisoformat(date_str)
    except (TypeError, ValueError):
        return None
    return (_today() - d).days


def load_cards(src: Path) -> list[dict]:
    out: list[dict] = []
    for p in sorted(src.glob("*.json")):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(r, dict) and "status" in r:
            out.append(r)
    return out


def _blocks_of(cards: list[dict]) -> dict[str, list[str]]:
    """Reverse of depends_on: id -> list of ids that depend on it."""
    out: dict[str, list[str]] = {}
    for c in cards:
        for dep in c.get("depends_on", []) or []:
            out.setdefault(dep, []).append(c["id"])
    return out


def _resolve_edge(target_id: str, by_id: dict[str, dict]) -> str:
    """Render an edge target as 'D-NNN (subject teaser)' if known."""
    target = by_id.get(target_id)
    if not target:
        return target_id
    teaser = target.get("subject", "")[:40]
    return f"{target_id} ({teaser})" if teaser else target_id


def _format_card(c: dict, blocks_map: dict[str, list[str]],
                 by_id: dict[str, dict]) -> list[str]:
    lines = [f"- **{c.get('id','?')}** — {c.get('subject','(no subject)')}"]
    sev = c.get("severity")
    if sev and sev != "unknown":
        lines[-1] += f"  *[{sev}]*"
    payoff = c.get("payoff", "")
    if payoff and payoff.strip():
        teaser = payoff[:120] + ("…" if len(payoff) > 120 else "")
        lines.append(f"  - payoff: {teaser}")
    deps = c.get("depends_on") or []
    if deps:
        rendered = ", ".join(_resolve_edge(d, by_id) for d in deps)
        lines.append(f"  - blocked-by: {rendered}")
    blocks = blocks_map.get(c.get("id", ""), [])
    if blocks:
        rendered = ", ".join(_resolve_edge(b, by_id) for b in blocks)
        lines.append(f"  - blocks: {rendered}")
    age = _age_days(c.get("last_updated_at", ""))
    if age is not None and age > 0:
        lines.append(f"  - age: {age}d")
    re_trigger = c.get("re_trigger", "")
    if re_trigger and re_trigger.strip():
        rt_teaser = re_trigger[:90] + ("…" if len(re_trigger) > 90 else "")
        lines.append(f"  - re-trigger: {rt_teaser}")
    return lines


def render(cards: list[dict], *, columns: list[str] | None = None,
           lanes: bool = True) -> str:
    blocks_map = _blocks_of(cards)
    by_id = {c.get("id", ""): c for c in cards if c.get("id")}
    by_status: dict[str, list[dict]] = {}
    for c in cards:
        by_status.setdefault(c["status"], []).append(c)
    if columns:
        col_order = columns
    else:
        col_order = sorted(by_status.keys())
    severity_order = ["load_bearing", "unknown", "cosmetic"]
    out: list[str] = []
    for col in col_order:
        bucket = by_status.get(col, [])
        out.append(f"## {col.upper()} ({len(bucket)})")
        out.append("")
        if not bucket:
            out.append("_(empty)_")
            out.append("")
            continue
        if lanes:
            by_lane: dict[str, list[dict]] = {}
            for c in bucket:
                by_lane.setdefault(c.get("severity", "unknown"), []).append(c)
            seen_lanes = [s for s in severity_order if s in by_lane] + \
                [s for s in by_lane if s not in severity_order]
            for lane in seen_lanes:
                out.append(f"### {lane}")
                for c in by_lane[lane]:
                    out.extend(_format_card(c, blocks_map, by_id))
                out.append("")
        else:
            for c in bucket:
                out.extend(_format_card(c, blocks_map, by_id))
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("usage: python -m boards.render <source_dir> [--columns a,b,c] [--no-lanes]")
        return 1
    src_arg = args[0]
    columns: list[str] | None = None
    lanes = True
    i = 1
    while i < len(args):
        if args[i] == "--columns" and i + 1 < len(args):
            columns = [c.strip() for c in args[i + 1].split(",") if c.strip()]
            i += 2
        elif args[i] == "--no-lanes":
            lanes = False
            i += 1
        else:
            i += 1
    src = Path(src_arg)
    if not src.is_absolute():
        src = REPO / src
    cards = load_cards(src)
    if not cards:
        print(f"no cards found in {src}")
        return 0
    print(f"# {src.name} — {len(cards)} cards\n")
    print(render(cards, columns=columns, lanes=lanes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
