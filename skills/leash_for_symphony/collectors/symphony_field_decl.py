"""Walks references/symphony-workflow-fields.txt and emits one data point
per recognized WORKFLOW.md front-matter field path. orchestrate.py
consults these data points (workflow_field_validity decision) to reject
candidate WORKFLOW.md files that contain a field outside the taxonomy."""
from __future__ import annotations

import hashlib
from pathlib import Path

from skills.leash_for_hooks.lib import data_point as dp

COLLECTOR_ID = "symphony_field_decl"
KIND = "symphony_field_decl"
VALUE_SCHEMA = {"type": "object", "required": ["field_path"],
                "properties": {"field_path": {"type": "string"}}}
INPUTS = ["skills/leash_for_symphony/references/symphony-workflow-fields.txt"]

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read_paths() -> list[str]:
    src = REPO_ROOT / INPUTS[0]
    out: list[str] = []
    for raw in src.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s.lower())
    return out


def compute_source_state() -> str:
    src = REPO_ROOT / INPUTS[0]
    return "sha256:" + hashlib.sha256(src.read_bytes()).hexdigest()[:32]


def _collector_pointer() -> dict:
    return {"kind": "collector", "target": {"collector_id": COLLECTOR_ID},
            "resolver": "collector_resolver",
            "bound_at": {"source_state": None, "resolved_at": None},
            "last_status": "unresolved", "last_payload": None, "last_reason": None}


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    return [
        dp.make_data_point(collector_id=COLLECTOR_ID, kind=KIND,
                           value={"field_path": fp},
                           source_state=source_state, collector_pointer=cp)
        for fp in _read_paths()
    ]


def verify(data_point: dict) -> tuple[str, str]:
    src = REPO_ROOT / INPUTS[0]
    if not src.exists():
        return "dangling", "source_missing"
    if data_point["value"]["field_path"] in _read_paths():
        return "live", "present"
    return "dangling", "field_path_removed"
