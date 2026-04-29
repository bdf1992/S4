"""Walks foundations/llm-sdk-denylist.txt and emits one data point per
entry. Foundation 2's no-LLM check on other collectors consults the
data points this collector produces (not the source file directly), so
that adding/removing an entry is visible as a data-point delta, not just
a file diff."""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..lib import data_point as dp

COLLECTOR_ID = "llm_sdk_denylist"
KIND = "llm_sdk_denylist_entry"
VALUE_SCHEMA = {"type": "object", "required": ["sdk_name"], "properties": {"sdk_name": {"type": "string"}}}
INPUTS = ["foundations/llm-sdk-denylist.txt"]

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read_lines() -> list[str]:
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
            value={"sdk_name": name},
            source_state=source_state,
            collector_pointer=cp,
        )
        for name in _read_lines()
    ]


def verify(data_point: dict) -> tuple[str, str]:
    src = REPO_ROOT / INPUTS[0]
    if not src.exists():
        return "dangling", "source_missing"
    name = data_point["value"]["sdk_name"]
    if name in _read_lines():
        return "live", "present"
    return "dangling", "entry_removed"
