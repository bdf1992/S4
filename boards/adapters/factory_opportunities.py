"""Adapter: factory opportunities — proposals + unaddressed gap-kinds → cards.

Card schema (column / lane / payload): see [boards/schema.md](../schema.md).
Columns mapped → proposed → promoted → rejected follow Anderson 2010's
workflow-state design.

Live-adapter shape (mirrors boards.adapters.grading_events). The dataset
collector at boards.collectors.factory_opportunities_cards is preferred
when present; this adapter is the fallback path the meta-board uses.

Usage:
  python -m boards.adapters.factory_opportunities
"""
from __future__ import annotations

from boards import render as renderer
from boards.collectors import factory_opportunities_cards as col

COLUMNS = ["mapped", "proposed", "promoted", "rejected"]


def cards() -> list[dict]:
    ss = col.compute_source_state()
    out: list[dict] = []
    for d in col.collect(ss):
        v = d["value"]
        flat = {
            "id": v["card_id"],
            "subject": v["subject"],
            "status": v["column"],
            "severity": v.get("lane"),
            "last_updated_at": v.get("last_updated_at"),
        }
        flat.update(v.get("payload", {}) or {})
        out.append(flat)
    return out


def main() -> int:
    cs = cards()
    if not cs:
        print("no factory opportunities found")
        return 0
    print(f"# factory-opportunities — {len(cs)} cards\n")
    print(renderer.render(cs, columns=COLUMNS, lanes=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
