"""Adapter: meta-board over all sub-board adapters.

Card schema (column / lane / payload): see [boards/schema.md](../schema.md).
The needs_attention vs healthy column axis is the cumulative-flow
projection cited there (Anderson 2010 §"Cumulative Flow Diagram"; Ries 2011).

Each sub-board's cards() function is invoked; the result is summarized
into one meta-card per board. Column axis is needs_attention vs healthy
(a board needs attention if it has any open + load_bearing cards).

Usage:
  python -m boards.adapters.all_boards
"""
from __future__ import annotations

import sys
from pathlib import Path

from boards import render as renderer
from boards.adapters import exemplars, factory_opportunities, grading_events
from boards.lib import cards as cards_lib
from debts import validate as _debts_validate

REPO = Path(__file__).resolve().parents[2]
COLUMNS = ["needs_attention", "healthy"]

OPEN_STATUSES = cards_lib.OPEN_STATUSES


def _debt_cards() -> list[dict]:
    out = []
    import json
    for p in sorted((REPO / "debts").glob("D-*.json")):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(r, dict) and "status" in r:
            out.append(r)
    return out


SUB_BOARDS = [
    ("debts", _debt_cards, "debts/"),
    ("grading-events", grading_events.cards, "foundations/grading-events.md"),
    ("exemplars", exemplars.cards, "skills/leash_*/exemplars/"),
    ("factory-opportunities", factory_opportunities.cards,
     "skills/gap_audit/ + proposals/ + approvals/"),
]


def _summarize(name: str, cards_fn, source: str) -> dict:
    cs = cards_fn()
    n_total = len(cs)
    n_open = sum(1 for c in cs if c.get("status") in OPEN_STATUSES)
    n_load_bearing_open = sum(
        1 for c in cs
        if c.get("status") in OPEN_STATUSES and c.get("severity") == "load_bearing"
    )
    last_dates = [c.get("last_updated_at") for c in cs if c.get("last_updated_at")]
    last_activity = max(last_dates) if last_dates else "-"
    status = "needs_attention" if n_load_bearing_open > 0 else "healthy"
    subject = (f"{n_total} cards · {n_open} open · "
               f"{n_load_bearing_open} load-bearing-open · last: {last_activity}")
    return {
        "id": name,
        "subject": subject,
        "status": status,
        "severity": "load_bearing" if status == "needs_attention" else "cosmetic",
        "last_updated_at": last_activity if last_activity != "-" else None,
        "payoff": f"source: {source}",
        "total": n_total,
        "open": n_open,
        "load_bearing_open": n_load_bearing_open,
        "source_label": source,
    }


def cards() -> list[dict]:
    return [_summarize(name, fn, src) for name, fn, src in SUB_BOARDS]


def main() -> int:
    cs = cards()
    print(f"# all-boards — meta-board over {len(cs)} sub-boards\n")
    print(renderer.render(cs, columns=COLUMNS, lanes=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
