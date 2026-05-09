"""Adapter: foundations/grading-events.md → kanban cards.

Card schema (column / lane / payload): see [boards/schema.md](../schema.md).
Status enum (pending / approved / resolved / rejected / superseded) is the
workflow-state column axis from Anderson 2010.

Parses H2 sections of the form
    ## Event NNN — <subject> (<STATUS>[ <YYYY-MM-DD>])
into baseline card shape and feeds them to boards.render.

Usage:
  python -m boards.adapters.grading_events
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from boards import render as renderer

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "foundations" / "grading-events.md"
COLUMNS = ["pending", "approved", "resolved", "rejected", "superseded"]

H2_PATTERN = re.compile(
    r"^##\s+Event\s+(\d+)\s+—\s+(.+?)\s+\(([A-Z]+)(?:\s+(\d{4}-\d{2}-\d{2}))?\)\s*$"
)


def cards() -> list[dict]:
    text = SOURCE.read_text(encoding="utf-8")
    out: list[dict] = []
    for line in text.splitlines():
        m = H2_PATTERN.match(line)
        if not m:
            continue
        num, subject, status, date = m.group(1), m.group(2), m.group(3), m.group(4)
        card = {
            "id": f"E-{int(num):03d}",
            "subject": subject.strip(),
            "status": status.lower(),
            "severity": "unknown",
        }
        if date:
            card["last_updated_at"] = date
        out.append(card)
    return out


def main() -> int:
    cs = cards()
    if not cs:
        print(f"no events parsed from {SOURCE.relative_to(REPO)}")
        return 0
    print(f"# grading-events — {len(cs)} cards (source: {SOURCE.relative_to(REPO)})\n")
    print(renderer.render(cs, columns=COLUMNS, lanes=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
