"""Walks operator-committed Symphony WORKFLOW.md candidates under
datasets/workflow-corpus/*.json and emits one data point per file.

Each input file is a pre-parsed JSON dict containing the YAML front
matter of a WORKFLOW.md. The on-disk corpus is JSON-shaped (not raw
WORKFLOW.md) so parsing stays deterministic and stdlib-only — the
operator commits the parsed dict and the leash never invokes a YAML
parser. The vocal_capture_plan.md emitted by orchestrate.py shows how
to format the parsed dict back into WORKFLOW.md form for shipping.

source_state hashes the (filename, content_hash) pairs in sorted order
so re-running against the same corpus yields the same hash."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from skills.leash_for_hooks.lib import data_point as dp

COLLECTOR_ID = "symphony_workflow"
KIND = "symphony_workflow"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["candidate_id", "field_paths", "permission_posture"],
}
INPUTS = ["skills/leash_for_symphony/datasets/workflow-corpus/*.json"]
CORPUS_DIR = Path(__file__).resolve().parents[1] / "datasets" / "workflow-corpus"


def _files() -> list[Path]:
    if not CORPUS_DIR.exists():
        return []
    return sorted(CORPUS_DIR.glob("*.json"))


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


def _flatten_paths(d: dict, prefix: str = "") -> list[str]:
    out: list[str] = []
    for k, v in sorted(d.items()):
        path = f"{prefix}{k}".lower()
        if isinstance(v, dict):
            out.extend(_flatten_paths(v, path + "."))
        else:
            out.append(path)
    return out


def _extract_posture(d: dict) -> dict:
    """Pull the four posture-relevant fields out of a parsed WORKFLOW dict.
    Missing fields are recorded as None (not absent) so the signal can
    distinguish 'operator did not set' from 'operator set to default'."""
    return {
        "claude_skip_permissions": (d.get("claude") or {}).get("skip_permissions"),
        "claude_permission_mode":  (d.get("claude") or {}).get("permission_mode"),
        "codex_approval_policy":   (d.get("codex")  or {}).get("approval_policy"),
        "codex_thread_sandbox":    (d.get("codex")  or {}).get("thread_sandbox"),
    }


def _walk_candidate(p: Path) -> dict:
    body = p.read_text(encoding="utf-8")
    parsed = json.loads(body)
    return {
        "candidate_id": p.stem,
        "field_paths": _flatten_paths(parsed),
        "permission_posture": _extract_posture(parsed),
        "byte_len": len(body.encode("utf-8")),
    }


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    out: list[dict] = []
    for p in _files():
        try:
            value = _walk_candidate(p)
        except (json.JSONDecodeError, OSError):
            continue
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND, value=value,
            source_state=source_state, collector_pointer=cp,
        ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    cid = data_point["value"]["candidate_id"]
    for p in _files():
        if p.stem != cid:
            continue
        try:
            fresh = _walk_candidate(p)
        except (json.JSONDecodeError, OSError):
            return "dangling", "candidate_unparseable"
        if fresh["field_paths"] == data_point["value"]["field_paths"] and \
           fresh["permission_posture"] == data_point["value"]["permission_posture"]:
            return "live", "present"
        return "dangling", "candidate_drifted"
    return "dangling", "candidate_removed"
