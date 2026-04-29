"""Resolver for pointer kind `collector`. Target shape: {collector_id}.
Returns the collector module's source path on `live`."""
from __future__ import annotations

from pathlib import Path

RESOLVER_ID = "collector_resolver"
POINTER_KIND = "collector"
COLLECTORS_DIR = Path(__file__).resolve().parents[1] / "collectors"


def resolve(target: dict, source_state: str) -> tuple[str, object]:
    if not isinstance(target, dict) or "collector_id" not in target:
        return "dangling", "bad_target_format"
    cid = target["collector_id"]
    if not isinstance(cid, str) or not cid:
        return "dangling", "bad_collector_id"
    candidate = COLLECTORS_DIR / f"{cid}.py"
    if not candidate.exists():
        return "dangling", "collector_module_missing"
    return "live", {"collector_id": cid, "path": str(candidate.relative_to(COLLECTORS_DIR.parents[2]))}
