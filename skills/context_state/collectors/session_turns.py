"""Foundation 2 collector — emits one data point per session-transcript record.

Walks Claude Code session JSONLs (and nested subagent transcripts) at
~/.claude/projects/<encoded-cwd>/ and projects each record into a
session.turn data point: role, byte size, what the record carried, and
running cumulative bytes within the session. The 1.0 floor any harness
self-state signal will rest on. Transcript dir is derived from __file__
via Claude Code's project-encoding convention (c:\\X\\Y -> c--X-Y).

See: foundations/collection-program.md, foundations/data-point.md.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from ..lib import data_point as dp

COLLECTOR_ID = "session_turns"
KIND = "session.turn"
VALUE_SCHEMA = {
    "type": "object",
    "required": [
        "session_id", "turn_index", "role", "byte_size",
        "cumulative_bytes_in_session",
    ],
    "properties": {
        "session_id": {"type": "string"},
        "turn_index": {"type": "integer"},
        "parent_uuid": {"type": ["string", "null"]},
        "role": {"type": "string"},
        "byte_size": {"type": "integer"},
        "has_tool_result": {"type": "boolean"},
        "attachment_kind": {"type": ["string", "null"]},
        "is_sidechain": {"type": "boolean"},
        "cumulative_bytes_in_session": {"type": "integer"},
    },
}
INPUTS = [
    "~/.claude/projects/<encoded-cwd>/*.jsonl",
    "~/.claude/projects/<encoded-cwd>/*/subagents/*.jsonl",
]
REPO_ROOT = Path(__file__).resolve().parents[3]
HOME = Path(os.path.expanduser("~"))


def _transcript_dir() -> Path:
    enc = str(REPO_ROOT).replace(":", "-").replace("\\", "-").replace("/", "-")
    return HOME / ".claude" / "projects" / enc


def _files() -> list[Path]:
    d = _transcript_dir()
    if not d.exists():
        return []
    return sorted(list(d.glob("*.jsonl")) + list(d.glob("*/subagents/*.jsonl")))


def compute_source_state() -> str:
    h = hashlib.sha256()
    files = _files()
    for p in files:
        rel = p.relative_to(_transcript_dir()).as_posix()
        h.update(rel.encode()); h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32] + ("+empty" if not files else "")


def _collector_pointer() -> dict:
    return {
        "kind": "collector", "target": {"collector_id": COLLECTOR_ID},
        "resolver": "collector_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved", "last_payload": None, "last_reason": None,
    }


def _classify(rec: dict) -> tuple[str, bool, str | None]:
    rtype = rec.get("type", "")
    msg = rec.get("message")
    if rtype in ("user", "assistant") and isinstance(msg, dict):
        role = msg.get("role") if isinstance(msg.get("role"), str) else rtype
        content = msg.get("content")
        has_tr = isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content
        )
        return role, has_tr, None
    if rtype == "attachment":
        att = rec.get("attachment", {})
        k = att.get("type") if isinstance(att, dict) else None
        return rtype, False, k if isinstance(k, str) else None
    return rtype if isinstance(rtype, str) else "", False, None


def _walk(p: Path) -> list[dict]:
    out: list[dict] = []
    cum, idx = 0, 0
    for raw in p.read_text(encoding="utf-8").splitlines():
        s = raw.rstrip()
        if not s:
            continue
        try:
            rec = json.loads(s)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        byte_size = len(s.encode("utf-8"))
        cum += byte_size
        role, has_tr, att = _classify(rec)
        parent = rec.get("parentUuid")
        out.append({
            "session_id": p.stem, "turn_index": idx,
            "parent_uuid": parent if isinstance(parent, str) else None,
            "role": role, "byte_size": byte_size,
            "has_tool_result": has_tr, "attachment_kind": att,
            "is_sidechain": bool(rec.get("isSidechain", False)),
            "cumulative_bytes_in_session": cum,
        })
        idx += 1
    return out


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    out: list[dict] = []
    for p in _files():
        for v in _walk(p):
            out.append(dp.make_data_point(
                collector_id=COLLECTOR_ID, kind=KIND, value=v,
                source_state=source_state, collector_pointer=cp,
            ))
    return out


def _find_session_file(sid: str) -> Path | None:
    d = _transcript_dir()
    if not d.exists():
        return None
    direct = d / f"{sid}.jsonl"
    if direct.exists():
        return direct
    nested = list(d.glob(f"*/subagents/{sid}.jsonl"))
    return nested[0] if nested else None


def verify(data_point: dict) -> tuple[str, str]:
    val = data_point["value"]
    p = _find_session_file(val["session_id"])
    if p is None:
        return "dangling", "session_file_missing"
    for v in _walk(p):
        if v["turn_index"] == val["turn_index"]:
            return ("live", "match") if v == val else ("dangling", "value_drift")
    return "dangling", "turn_index_out_of_range"
