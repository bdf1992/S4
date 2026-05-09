"""Unified entry point for the boards system.

Card schema (column / lane / payload, render-shape projection): see
[boards/schema.md](schema.md). Pays D-006 by formalizing the geometry
against published kanban traditions (Anderson 2010, Atlassian Jira,
Anderson/Ries CFD).

Usage:
  python -m boards                            # list available boards
  python -m boards collect <name>             # run F2 collector, write dataset
  python -m boards <name>                     # render named board (markdown)
  python -m boards <name> --no-lanes
  python -m boards <name> --html              # HTML kanban to stdout
  python -m boards <name> --html -o page.html # HTML kanban to file

Render commands read from the dataset (boards/datasets/<name>_cards.jsonl).
A board with no dataset renders empty — run `python -m boards collect <name>`
first.
"""
from __future__ import annotations

import sys
from pathlib import Path

from boards import render as renderer
from boards import render_html as html_renderer
from boards.lib import cards as cards_lib

REPO = Path(__file__).resolve().parents[1]


BOARDS: dict[str, dict] = {
    "debts": {
        "describe": "Open / closed gaps with re-triggers (debts/D-*.json)",
        "collector": "boards.collectors.debts_cards",
        "columns": ["open", "parked", "closed_paid", "closed_written_off", "superseded"],
        "lanes": True,
        "source_label": "debts/",
    },
    "grading-events": {
        "describe": "Foundation grading events parsed from foundations/grading-events.md",
        "collector": "boards.collectors.grading_events_cards",
        "columns": ["pending", "approved", "resolved", "rejected", "superseded"],
        "lanes": False,
        "source_label": "foundations/grading-events.md",
    },
    "exemplars": {
        "describe": "Bundles awaiting promotion across all leashes",
        "collector": "boards.collectors.exemplars_cards",
        "columns": ["proposed", "promoted"],
        "lanes": False,
        "source_label": "skills/",
    },
    "factory-opportunities": {
        "describe": "Stakable factories: open proposals + unaddressed gap-kinds",
        "collector": "boards.collectors.factory_opportunities_cards",
        "columns": ["mapped", "proposed", "promoted", "rejected"],
        "lanes": False,
        "source_label": "skills/gap_audit/ + proposals/ + approvals/",
    },
    "all": {
        "describe": "Meta-board: needs_attention vs healthy across every sub-board",
        "collector": "boards.collectors.all_cards",
        "columns": ["needs_attention", "healthy"],
        "lanes": True,
        "source_label": None,
    },
}


def _list_boards() -> int:
    print("Available boards:\n")
    width = max(len(n) for n in BOARDS) + 2
    for name, meta in BOARDS.items():
        marker = " *" if cards_lib.has_dataset(name) else "  "
        print(f"{marker}{name:<{width}}  {meta['describe']}")
    print(
        "\n* = dataset present (boards/datasets/<name>_cards.jsonl).\n"
        "Usage: python -m boards collect <name>\n"
        "       python -m boards <name> [--no-lanes] [--html [-o page.html]]"
    )
    return 0


def _cards_for(name: str) -> list[dict]:
    return cards_lib.cards_from_dataset(name)


def _collect(name: str) -> int:
    if name not in BOARDS:
        print(f"unknown board: {name}", file=sys.stderr)
        return 2
    meta = BOARDS[name]
    from importlib import import_module
    from boards.lib import data_point as dp
    mod = import_module(meta["collector"])
    ss = mod.compute_source_state()
    dps = mod.collect(ss)
    bad = [(d, dp.validate(d)) for d in dps]
    invalid = [(d, r) for d, (ok, r) in bad if not ok]
    if invalid:
        for d, r in invalid:
            print(f"INVALID {d.get('id')}: {r}", file=sys.stderr)
        return 1
    out_path = cards_lib.dataset_path(name)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dp.write_jsonl(out_path, dps)
    (out_path.with_suffix(".source_state")).write_text(ss + "\n", encoding="utf-8")
    print(f"{name}: {len(dps)} data points -> {out_path}")
    return 0


def _render_board(name: str, *, no_lanes: bool) -> int:
    if name not in BOARDS:
        print(f"unknown board: {name}\n")
        return _list_boards()
    meta = BOARDS[name]
    cards = _cards_for(name)
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


def _vsc(rel_path: str) -> str:
    return f"vscode://file/{(REPO / rel_path).resolve().as_posix()}"


def _leaf_link_fn(name: str):
    """Map a leaf-board card to a vscode://file/ URI for its source."""
    if name == "debts":
        return lambda c: _vsc(f"debts/{c.get('id')}.json")
    if name == "grading-events":
        return lambda c: _vsc("foundations/grading-events.md")
    if name == "exemplars":
        def fn(c):
            cid = c.get("id", "")
            parts = cid.split("/")
            if len(parts) == 3:
                leash, col, bundle = parts
                return _vsc(f"skills/{leash}/exemplars/{col}/{bundle}.json")
            return None
        return fn
    if name == "factory-opportunities":
        def fn(c):
            cid = c.get("id", "")
            if cid.startswith("gap-kind:"):
                return _vsc("skills/gap_audit/datasets/")
            parts = cid.split(":")
            if len(parts) == 3 and parts[0] == "prop":
                return _vsc(f"proposals/prop_{parts[1]}_{parts[2]}/proposal.json")
            return None
        return fn
    return None


def _meta_link_fn(out_dir: Path | None):
    """Map a meta-card (card_id is leaf board name) to its sibling HTML file."""
    if out_dir is None:
        return None
    return lambda c: f"{c.get('id')}.html"


def _render_board_html(name: str, *, no_lanes: bool, out_path: Path | None) -> int:
    if name not in BOARDS:
        print(f"unknown board: {name}\n")
        return _list_boards()
    meta = BOARDS[name]
    cards = _cards_for(name)

    if name == "all":
        link_fn = _meta_link_fn(out_path.parent if out_path else None)
    else:
        link_fn = _leaf_link_fn(name) if out_path else None

    page = html_renderer.render_html(
        cards,
        board_name=name,
        source_label=meta.get("source_label"),
        columns=meta["columns"],
        lanes=meta["lanes"] and not no_lanes,
        card_link_fn=link_fn,
    )
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page, encoding="utf-8")
        sys.stderr.write(f"wrote {out_path}\n")
        if name == "all":
            for leaf in ("debts", "grading-events", "exemplars", "factory-opportunities"):
                if leaf not in BOARDS:
                    continue
                leaf_meta = BOARDS[leaf]
                leaf_cards = _cards_for(leaf)
                leaf_page = html_renderer.render_html(
                    leaf_cards,
                    board_name=leaf,
                    source_label=leaf_meta.get("source_label"),
                    columns=leaf_meta["columns"],
                    lanes=leaf_meta["lanes"] and not no_lanes,
                    card_link_fn=_leaf_link_fn(leaf),
                )
                leaf_out = out_path.parent / f"{leaf}.html"
                leaf_out.write_text(leaf_page, encoding="utf-8")
                sys.stderr.write(f"wrote {leaf_out}\n")
    else:
        sys.stdout.write(page)
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        return _list_boards()
    if args[0] == "collect":
        if len(args) < 2:
            print("usage: python -m boards collect <name>", file=sys.stderr)
            return 2
        return _collect(args[1])
    name = args[0]
    rest = args[1:]
    no_lanes = "--no-lanes" in rest
    if "--html" in rest:
        out_path: Path | None = None
        if "-o" in rest:
            i = rest.index("-o")
            if i + 1 < len(rest):
                out_path = Path(rest[i + 1])
        return _render_board_html(name, no_lanes=no_lanes, out_path=out_path)
    return _render_board(name, no_lanes=no_lanes)


if __name__ == "__main__":
    raise SystemExit(main())
