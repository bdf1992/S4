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
    out: list[tuple[str, Path]] = []
    for pat in INPUTS:
        p = _expand(pat)
        if p.exists() and p.is_file():
            out.append((pat, p))
    return out


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


def _walk_settings(pat: str, p: Path) -> list[dict]:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    rows: list[dict] = []
    hooks_block = data.get("hooks", {}) if isinstance(data, dict) else {}
    if not isinstance(hooks_block, dict):
        return []
    for event, matcher_list in hooks_block.items():
        if not isinstance(matcher_list, list):
            continue
        for m_entry in matcher_list:
            if not isinstance(m_entry, dict):
                continue
            matcher = m_entry.get("matcher", "")
            inner = m_entry.get("hooks", [])
            if not isinstance(inner, list):
                continue
            for idx, h in enumerate(inner):
                if not isinstance(h, dict):
                    continue
                cmd = h.get("command", "")
                if not isinstance(cmd, str):
                    continue
                rows.append({
                    "scope": _scope_of(pat), "settings_path": pat,
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
    fresh = _walk_settings(pat, p)
    for row in fresh:
        if (row["event"] == v["event"] and row["matcher"] == v["matcher"]
                and row["hook_index"] == v["hook_index"]
                and row["command_hash"] == v["command_hash"]):
            return "live", "present"
    return "dangling", "hook_changed_or_removed"
