"""Walks exemplars/promoted/*.json and emits one data point per
human-promoted exemplar bundle state. The emission_readiness signal
fits on the data points this collector produces.

On first run (and every run until a human promotes an exemplar) this
collector emits zero data points; emission_readiness's fit is therefore
degenerate; the leash emits sub-0.4 candidates honestly.

Promotion protocol (out of scope for this code, codified for the human):
  1. orchestrate.py writes proposed bundle states to exemplars/proposed/
  2. A human reviews and copies the file to exemplars/promoted/
  3. Next run, this collector picks it up.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..lib import data_point as dp

COLLECTOR_ID = "exemplar_bundle_state"
KIND = "exemplar_bundle_state"
VALUE_SCHEMA = {"type": "object", "required": ["bundle_id", "dataset_sizes"]}
INPUTS = ["skills/leash_for_hooks/exemplars/promoted/*.json"]
PROMOTED_DIR = Path(__file__).resolve().parents[1] / "exemplars" / "promoted"


def _files() -> list[Path]:
    if not PROMOTED_DIR.exists():
        return []
    return sorted(PROMOTED_DIR.glob("*.json"))


def compute_source_state() -> str:
    h = hashlib.sha256()
    for p in _files():
        h.update(p.name.encode()); h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32] + ("+empty" if not _files() else "")


def _collector_pointer() -> dict:
    return {"kind": "collector", "target": {"collector_id": COLLECTOR_ID},
            "resolver": "collector_resolver",
            "bound_at": {"source_state": None, "resolved_at": None},
            "last_status": "unresolved", "last_payload": None, "last_reason": None}


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    out: list[dict] = []
    for p in _files():
        try:
            v = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not (isinstance(v, dict) and "bundle_id" in v and "dataset_sizes" in v):
            continue
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND, value=v,
            source_state=source_state, collector_pointer=cp,
        ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    bid = data_point["value"]["bundle_id"]
    for p in _files():
        try:
            v = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if v.get("bundle_id") == bid:
            return "live", "present"
    return "dangling", "exemplar_removed"
