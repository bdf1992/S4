"""Walks references/slash-command-taxonomy.txt and emits one data point
per reserved slash-command name. orchestrate.py consults these data
points (name_validity decision) to reject candidates that would shadow
a reserved name."""
from __future__ import annotations

import hashlib
from pathlib import Path

from skills.leash_for_hooks.lib import data_point as dp

COLLECTOR_ID = "slash_command_decl"
KIND = "slash_command_decl"
VALUE_SCHEMA = {"type": "object", "required": ["name"],
                "properties": {"name": {"type": "string"}}}
INPUTS = ["skills/leash_for_slash_commands/references/slash-command-taxonomy.txt"]

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read_names() -> list[str]:
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
                           value={"name": name},
                           source_state=source_state, collector_pointer=cp)
        for name in _read_names()
    ]


def verify(data_point: dict) -> tuple[str, str]:
    src = REPO_ROOT / INPUTS[0]
    if not src.exists():
        return "dangling", "source_missing"
    if data_point["value"]["name"] in _read_names():
        return "live", "present"
    return "dangling", "name_removed"
