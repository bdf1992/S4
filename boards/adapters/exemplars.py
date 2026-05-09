"""Adapter: skills/leash_*/exemplars/{proposed,promoted}/*.json → kanban cards.

Card schema (column / lane / payload): see [boards/schema.md](../schema.md).
Column axis (proposed → promoted) is the workflow-state design from
Anderson 2010; no lane axis here.

The directory name (proposed | promoted) is the status column. Each
exemplar bundle becomes one card across all leashes. Demonstrates a
directory-as-column projection — different source shape from debts/
(structured records) and grading-events (parsed prose).

Usage:
  python -m boards.adapters.exemplars
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

from boards import render as renderer

REPO = Path(__file__).resolve().parents[2]
COLUMNS = ["proposed", "promoted"]


def cards() -> list[dict]:
    out: list[dict] = []
    for leash_dir in sorted(REPO.glob("skills/leash_*")):
        for status in COLUMNS:
            d = leash_dir / "exemplars" / status
            if not d.is_dir():
                continue
            for p in sorted(d.glob("*.json")):
                try:
                    raw = json.loads(p.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                bundle_id = raw.get("bundle_id", p.stem) if isinstance(raw, dict) else p.stem
                mtime = _dt.date.fromtimestamp(p.stat().st_mtime).isoformat()
                out.append({
                    "id": bundle_id,
                    "subject": f"{leash_dir.name}: dataset_sizes={raw.get('dataset_sizes', {}) if isinstance(raw, dict) else {}}",
                    "status": status,
                    "severity": "load_bearing" if status == "promoted" else "unknown",
                    "last_updated_at": mtime,
                })
    return out


def main() -> int:
    cs = cards()
    if not cs:
        print("no exemplar bundles found")
        return 0
    print(f"# exemplars — {len(cs)} cards (across all leashes)\n")
    print(renderer.render(cs, columns=COLUMNS, lanes=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
