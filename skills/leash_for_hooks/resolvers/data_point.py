"""Resolver for pointer kind `data_point`. Target shape: {dp_id}.
Walks the dataset jsonl files in `datasets/` and returns the matching
record on `live`."""
from __future__ import annotations

import json
from pathlib import Path

RESOLVER_ID = "data_point_resolver"
POINTER_KIND = "data_point"
DATASETS_DIR = Path(__file__).resolve().parents[1] / "datasets"


def resolve(target: dict, source_state: str) -> tuple[str, object]:
    if not isinstance(target, dict) or "dp_id" not in target:
        return "dangling", "bad_target_format"
    dp_id = target["dp_id"]
    if not isinstance(dp_id, str) or ":" not in dp_id:
        return "dangling", "bad_dp_id"
    if not DATASETS_DIR.exists():
        return "dangling", "datasets_dir_missing"
    for jsonl in sorted(DATASETS_DIR.glob("*.jsonl")):
        for raw in jsonl.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if rec.get("id") == dp_id:
                return "live", rec
    return "dangling", "data_point_not_found"
