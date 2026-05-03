"""Cook session record — structured output for cook ritual under heartbeat.

Cook is a generative 3.0 ritual (subagent goes heads-down on a target).
When dispatched via heartbeat fan_out, each cook session writes a session
record so the runner can aggregate (and so future reads can reason about
what was attempted).

This module is the cook ritual's output_writer surface. The runner does
NOT call these functions itself — they are called by the *dispatched
subagent* when its session ends. For shadow-design hand-plays where real
subagent dispatch is unavailable, the runner may call record_session()
directly to simulate what a subagent would have written.

Gate is target-aware: a cook for target X at git HEAD H fires iff no
prior receipt exists for (X, H). This keeps fan_out re-runs idempotent
per item, even when the chain itself re-fires.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO), capture_output=True, text=True, check=True,
    ).stdout.strip()


def cook_gate(receipt_dir: str | Path,
              state: dict | None = None) -> bool:
    """Fire iff no prior cook receipt exists for (target, git_head).

    state must include 'target' (the skill or path the cook will work on);
    'mode' is read if present, defaults to 'solve'."""
    if not state or "target" not in state:
        return True
    rd = Path(receipt_dir)
    if not rd.is_absolute():
        rd = REPO / rd
    head = _git_head()
    target = state["target"]
    needle = f"{head[:12]}::{target}"
    if not rd.is_dir():
        return True
    for p in rd.glob("*.receipt.json"):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if rec.get("idempotency_key", "").startswith(needle):
            return False
    return True


def cook_idempotency_key(receipt_dir: str | Path,
                         state: dict | None = None) -> str:
    """Idempotency key for cook: git HEAD + target + mode. Two cook
    invocations with the same key collapse to one fire."""
    state = state or {}
    target = state.get("target", "<no-target>")
    mode = state.get("mode", "solve")
    head = _git_head()
    return f"{head[:12]}::{target}::{mode}"


def record_session(target: str, mode: str = "solve",
                   started_at: str | None = None,
                   ended_at: str | None = None,
                   commits_landed: list[str] | None = None,
                   net_loc: int = 0,
                   files_touched: int = 0,
                   showcase: str = "",
                   exit_code: int = 0,
                   surface: str = "agent-subagent") -> dict:
    """Build the structured cook session record. Schema lives at
    schemas/cook_output.json (mirrors the dict returned here)."""
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    sid_seed = f"{target}::{mode}::{started_at or now}"
    session_id = hashlib.sha256(sid_seed.encode()).hexdigest()[:12]
    return {
        "schema_version": "0.1",
        "ritual_id": "ritual:cook",
        "session_id": session_id,
        "target": target,
        "mode": mode,
        "surface": surface,
        "started_at": started_at or now,
        "ended_at": ended_at or now,
        "commits_landed": commits_landed or [],
        "net_loc": net_loc,
        "files_touched": files_touched,
        "showcase": showcase,
        "exit_code": exit_code,
        "git_head_at_record": _git_head(),
    }


def write_session(target: str, output_dir: str | Path, **kwargs) -> Path:
    """Persist a session record under output_dir keyed by session_id."""
    rec = record_session(target, **kwargs)
    od = Path(output_dir)
    if not od.is_absolute():
        od = REPO / od
    od.mkdir(parents=True, exist_ok=True)
    out_path = od / f"{rec['session_id']}.json"
    out_path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return out_path
