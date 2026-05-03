"""Walk this skill's emitted bundles and return their history rows.

Pure 0.1 infrastructure: filesystem walk + JSON parse, no LLM, no
nondeterminism. Encodes the bundle layout (`outputs/run-*/stats.json`,
the `data["stats"]` envelope, the `floor_ratio` / `by_regime` /
`by_skill` field names) in *one* place — the producer.

Peer skills that want a chronological view of how the floor moved
(e.g. dashboard's `_audit_history`) call `bundles_history()` instead of
hard-coding the bundle path and field names. That keeps the contract
between producer and consumer in a single file: when the bundle layout
shifts, the consumers do not silently fall through to empty defaults.

The returned rows are intentionally a flat list of plain dicts — not
data points, since these are derived observations (the producer is the
collector; this module is just a reader). One row per bundle that has a
parseable `stats.json`, sorted oldest-first by mtime.
"""
from __future__ import annotations

import json
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
OUTPUTS = SKILL / "outputs"


def bundles_history() -> list[dict]:
    """Return [{bundle_id, mtime, floor_ratio, by_regime, by_skill}, ...].

    Oldest first by mtime. Bundles missing `stats.json` or with malformed
    JSON are skipped silently — the caller gets only rows it can use.
    """
    if not OUTPUTS.is_dir():
        return []
    rows: list[dict] = []
    for run_dir in sorted(OUTPUTS.glob("run-*"), key=lambda p: p.stat().st_mtime):
        stats_path = run_dir / "stats.json"
        if not stats_path.exists():
            continue
        try:
            data = json.loads(stats_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        s = data.get("stats", {})
        rows.append({
            "bundle_id": run_dir.name,
            "mtime": int(stats_path.stat().st_mtime),
            "floor_ratio": s.get("floor_ratio"),
            "by_regime": s.get("by_regime", {}),
            "by_skill": s.get("by_skill", {}),
        })
    return rows
