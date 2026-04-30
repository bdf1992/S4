"""Walks Claude Code slash-command markdown files in user and project
scopes and emits one data point per discovered command. Each `.md` file
under `commands/` defines a slash command whose name is the file stem.
source_state hashes the (normalized_path, content_hash) pairs in sorted
order so re-running against the same filesystem yields the same hash."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from skills.leash_for_hooks.lib import data_point as dp

COLLECTOR_ID = "slash_command_config"
KIND = "slash_command_config"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["scope", "commands_path", "name", "name_hash", "byte_len"],
}
REPO_ROOT = Path(__file__).resolve().parents[3]
HOME = Path(os.path.expanduser("~"))
INPUTS = [
    "~/.claude/commands/*.md",
    "<repo>/.claude/commands/*.md",
]


def _expand(pat: str) -> list[Path]:
    if pat.startswith("~/"):
        base = HOME / pat[2:].split("*", 1)[0]
    elif pat.startswith("<repo>/"):
        base = REPO_ROOT / pat[len("<repo>/"):].split("*", 1)[0]
    else:
        raise ValueError(f"unrecognized input pattern: {pat}")
    suffix = pat.split("/")[-1]
    if not base.exists():
        return []
    return sorted(base.glob(suffix))


def _scope_of(pat: str) -> str:
    return {"~/.claude/commands/*.md": "user",
            "<repo>/.claude/commands/*.md": "project"}[pat]


def _discover() -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for pat in INPUTS:
        for p in _expand(pat):
            if p.is_file():
                out.append((pat, p))
    return out


def compute_source_state() -> str:
    h = hashlib.sha256()
    found = _discover()
    for pat, p in found:
        h.update(pat.encode()); h.update(b"\0")
        h.update(p.name.encode()); h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32] + ("+empty" if not found else "")


def _collector_pointer() -> dict:
    return {"kind": "collector", "target": {"collector_id": COLLECTOR_ID},
            "resolver": "collector_resolver",
            "bound_at": {"source_state": None, "resolved_at": None},
            "last_status": "unresolved", "last_payload": None, "last_reason": None}


def _walk_command(pat: str, p: Path) -> dict:
    name = p.stem.lower()
    body = p.read_bytes()
    return {
        "scope": _scope_of(pat),
        "commands_path": pat,
        "name": name,
        "name_hash": "sha256:" + hashlib.sha256(name.encode()).hexdigest()[:16],
        "byte_len": len(body),
    }


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    out: list[dict] = []
    for pat, p in _discover():
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND, value=_walk_command(pat, p),
            source_state=source_state, collector_pointer=cp,
        ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    v = data_point["value"]
    pat = v["commands_path"]
    try:
        candidates = _expand(pat)
    except ValueError:
        return "dangling", "bad_pattern"
    for p in candidates:
        if p.stem.lower() == v["name"]:
            fresh = _walk_command(pat, p)
            if fresh["name_hash"] == v["name_hash"]:
                return "live", "present"
    return "dangling", "command_removed_or_renamed"
