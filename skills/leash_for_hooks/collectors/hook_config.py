"""Walks Claude Code settings.json files in the four standard scopes and
emits one data point per declared hook command. Glob patterns in INPUTS
resolve at compute_source_state() time; source_state hashes the
(normalized_path, content_hash) pairs in sorted order so re-running
against an identical filesystem state yields an identical hash."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from ..lib import data_point as dp

COLLECTOR_ID = "hook_config"
KIND = "hook_config"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["scope", "settings_path", "event", "matcher", "hook_index", "command", "command_hash"],
}
REPO_ROOT = Path(__file__).resolve().parents[3]
HOME = Path(os.path.expanduser("~"))
INPUTS = [
    "~/.claude/settings.json",
    "~/.claude/settings.local.json",
    "<repo>/.claude/settings.json",
    "<repo>/.claude/settings.local.json",
]


def _expand(pat: str) -> Path:
    if pat.startswith("~/"):
        return HOME / pat[2:]
    if pat.startswith("<repo>/"):
        return REPO_ROOT / pat[len("<repo>/") :]
    raise ValueError(f"unrecognized input pattern: {pat}")


def _scope_of(pat: str) -> str:
    return {
        "~/.claude/settings.json": "user",
        "~/.claude/settings.local.json": "user-local",
        "<repo>/.claude/settings.json": "project",
        "<repo>/.claude/settings.local.json": "project-local",
    }[pat]


def _discover() -> list[tuple[str, Path]]:
    candidates = [(pat, _expand(pat)) for pat in INPUTS]
    return [(pat, p) for pat, p in candidates if p.is_file()]


def compute_source_state() -> str:
    h = hashlib.sha256()
    for pat, p in _discover():
        h.update(pat.encode())
        h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32] + ("+empty" if not _discover() else "")


def _collector_pointer() -> dict:
    return {
        "kind": "collector", "target": {"collector_id": COLLECTOR_ID},
        "resolver": "collector_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved", "last_payload": None, "last_reason": None,
    }


def _safe(x, t):
    """Centralized type-guard: return x if it's an instance of t, else an empty t().
    Absorbs all isinstance-checks for malformed external JSON into one place."""
    return x if isinstance(x, t) else t()


def _walk_settings(pat: str, p: Path) -> list[dict]:
    try:
        data = _safe(json.loads(p.read_text(encoding="utf-8")), dict)
    except json.JSONDecodeError:
        return []
    scope = _scope_of(pat)
    rows: list[dict] = []
    for event, matcher_list in _safe(data.get("hooks"), dict).items():
        for m_entry in _safe(matcher_list, list):
            m = _safe(m_entry, dict)
            matcher = m.get("matcher", "")
            for idx, h_entry in enumerate(_safe(m.get("hooks"), list)):
                cmd = _safe(h_entry, dict).get("command", "")
                if isinstance(cmd, str):
                    rows.append({
                        "scope": scope, "settings_path": pat,
                        "event": event, "matcher": matcher, "hook_index": idx,
                        "command": cmd,
                        "command_hash": "sha256:" + hashlib.sha256(cmd.encode()).hexdigest()[:16],
                    })
    return rows


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    out: list[dict] = []
    for pat, p in _discover():
        for v in _walk_settings(pat, p):
            out.append(dp.make_data_point(
                collector_id=COLLECTOR_ID, kind=KIND, value=v,
                source_state=source_state, collector_pointer=cp,
            ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    v = data_point["value"]
    pat = v["settings_path"]
    try:
        p = _expand(pat)
    except ValueError:
        return "dangling", "bad_pattern"
    if not p.exists():
        return "dangling", "settings_file_missing"
    key = (v["event"], v["matcher"], v["hook_index"], v["command_hash"])
    fresh = {(r["event"], r["matcher"], r["hook_index"], r["command_hash"])
             for r in _walk_settings(pat, p)}
    return ("live", "present") if key in fresh else ("dangling", "hook_changed_or_removed")
