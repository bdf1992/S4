"""Walks references/hook-events.txt and emits one data point per declared
event name. The leash's orchestration consults these data points to
validate that a candidate hook targets a known event."""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..lib import data_point as dp

COLLECTOR_ID = "hook_event_decl"
KIND = "hook_event_decl"
VALUE_SCHEMA = {"type": "object", "required": ["event"], "properties": {"event": {"type": "string"}}}
INPUTS = ["skills/leash_for_hooks/references/hook-events.txt"]

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read_events() -> list[str]:
    src = REPO_ROOT / INPUTS[0]
    out: list[str] = []
    for raw in src.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


def compute_source_state() -> str:
    src = REPO_ROOT / INPUTS[0]
    return "sha256:" + hashlib.sha256(src.read_bytes()).hexdigest()[:32]


def _collector_pointer() -> dict:
    return {
        "kind": "collector",
        "target": {"collector_id": COLLECTOR_ID},
        "resolver": "collector_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved",
        "last_payload": None,
        "last_reason": None,
    }


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    return [
        dp.make_data_point(
            collector_id=COLLECTOR_ID,
            kind=KIND,
            value={"event": ev},
            source_state=source_state,
            collector_pointer=cp,
        )
        for ev in _read_events()
    ]


def verify(data_point: dict) -> tuple[str, str]:
    src = REPO_ROOT / INPUTS[0]
    if not src.exists():
        return "dangling", "source_missing"
    if data_point["value"]["event"] in _read_events():
        return "live", "present"
    return "dangling", "event_removed"
