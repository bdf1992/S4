"""Unified entry point for the boards system.

Usage:
  python -m boards                  # list available boards
  python -m boards <name>           # render named board
  python -m boards <name> --no-lanes
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from boards import render as renderer

REPO = Path(__file__).resolve().parents[1]


def _debt_cards() -> list[dict]:
    out: list[dict] = []
    for p in sorted((REPO / "debts").glob("D-*.json")):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(r, dict) and "status" in r:
            out.append(r)
    return out


def _adapter_cards(module_name: str):
    """Lazy-load an adapter module and return its cards()."""
    from importlib import import_module
    mod = import_module(f"boards.adapters.{module_name}")
    return mod.cards()


BOARDS: dict[str, dict] = {
    "debts": {
        "describe": "Open / closed gaps with re-triggers (debts/D-*.json)",
        "cards": _debt_cards,
        "columns": ["open", "parked", "closed_paid", "closed_written_off", "superseded"],
        "lanes": True,
    },
    "grading-events": {
        "describe": "Foundation grading events parsed from foundations/grading-events.md",
        "cards": lambda: _adapter_cards("grading_events"),
        "columns": ["pending", "approved", "resolved", "rejected", "superseded"],
        "lanes": False,
    },
    "exemplars": {
        "describe": "Bundles awaiting promotion across all leashes",
        "cards": lambda: _adapter_cards("exemplars"),
        "columns": ["proposed", "promoted"],
        "lanes": False,
    },
    "all": {
        "describe": "Meta-board: needs_attention vs healthy across every sub-board",
        "cards": lambda: _adapter_cards("all_boards"),
        "columns": ["needs_attention", "healthy"],
        "lanes": True,
    },
}


def _list_boards() -> int:
    print("Available boards:\n")
    width = max(len(n) for n in BOARDS) + 2
    for name, meta in BOARDS.items():
        print(f"  {name:<{width}}  {meta['describe']}")
    print(f"\nUsage: python -m boards <name> [--no-lanes]")
    return 0


def _render_board(name: str, *, no_lanes: bool) -> int:
    if name not in BOARDS:
        print(f"unknown board: {name}\n")
        return _list_boards()
    meta = BOARDS[name]
    cards = meta["cards"]()
    if not cards:
        print(f"# {name}\n\n_(no cards)_")
        return 0
    print(f"# {name} — {len(cards)} cards\n")
    print(renderer.render(
        cards,
        columns=meta["columns"],
        lanes=meta["lanes"] and not no_lanes,
    ))
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        return _list_boards()
    name = args[0]
    no_lanes = "--no-lanes" in args[1:]
    return _render_board(name, no_lanes=no_lanes)


if __name__ == "__main__":
    raise SystemExit(main())
