"""Foundation 1 collector — cook events from Claude Code session transcripts.

The diagnosis behind this collector: /cook receipts ship as prose
(showcase + receipts in the closing message) and only the prose is
preserved per-session. To answer "how is the experiment compounding
across N cooks?" the operator currently re-reads N markdown blobs.
This is the asymmetric exit: pre-cook is grounded by
[tools/cook_grounding.py](cook_grounding.py); post-cook had no
structured emission. This collector closes that asymmetry by walking
session jsonl transcripts (operator-intent primary data per memory)
and emitting one data point per `/cook` invocation, with
**numeric/categorical fields** that aggregate into trends — cadence,
duration, mode mix, target frequency, message volume — so a
downstream renderer can plot them across N events.

Source walked: ~/.claude/projects/<repo-slug>/*.jsonl
Each cook invocation in a session is detected by the
`<command-name>/cook</command-name>` marker in a user message.
Multiple invocations within one session are sequenced; each cook's
window ends at the next cook in the same session, or at the last
recorded entry of the session.

Run via:
  python -m tools.cook_event              # human-readable summary
  python -m tools.cook_event --jsonl      # data points to stdout

See: foundations/data-point.md, foundations/collection-program.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from boards.lib import data_point as dp

COLLECTOR_ID = "cook_event"
KIND = "cook_event"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["session_id", "invoked_at", "ended_at", "mode", "target",
                 "messages_count", "tool_calls_count", "git_branch"],
    "properties": {
        "session_id": {"type": "string"},
        "invoked_at": {"type": "string"},
        "ended_at": {"type": "string"},
        "mode": {"enum": ["solve", "concept"]},
        "target": {"type": ["string", "null"]},
        "messages_count": {"type": "integer"},
        "tool_calls_count": {"type": "integer"},
        "git_branch": {"type": ["string", "null"]},
    },
}

REPO = Path(__file__).resolve().parents[1]
HOME = Path(os.path.expanduser("~"))
PROJECT_SLUG = "c--Users-bdf19-Desktop-zero-four-experiment"
SESSIONS_DIR = HOME / ".claude" / "projects" / PROJECT_SLUG
INPUTS = [f"{SESSIONS_DIR.as_posix()}/*.jsonl"]

COMMAND_RE = re.compile(r"<command-name>/cook</command-name>")
ARGS_RE = re.compile(r"<command-args>([^<]*)</command-args>")
KNOWN_MODES = ("solve", "concept")


def _session_files() -> list[Path]:
    if not SESSIONS_DIR.exists():
        return []
    return sorted(p for p in SESSIONS_DIR.glob("*.jsonl") if p.is_file())


def _parse_args(text: str) -> tuple[str, str | None] | None:
    """Parse a /cook user message into (mode, target). Returns None if
    the message is not a /cook invocation."""
    if not COMMAND_RE.search(text):
        return None
    m = ARGS_RE.search(text)
    raw = (m.group(1) if m else "").strip()
    if not raw:
        return "solve", None
    parts = raw.split(None, 1)
    if parts[0] in KNOWN_MODES:
        return parts[0], parts[1] if len(parts) > 1 else None
    return "solve", raw


def _user_text(rec: dict) -> str:
    msg = rec.get("message", {})
    c = msg.get("content", "")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        for blk in c:
            if isinstance(blk, dict) and blk.get("type") == "text":
                return blk.get("text", "") or ""
    return ""


def _walk_session(path: Path) -> list[dict]:
    """Returns one value-dict per /cook invocation in this session."""
    invocs: list[dict] = []
    last_ts = ""
    user_n = 0
    tool_n = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            ts = rec.get("timestamp") or ""
            if ts:
                last_ts = ts
            t = rec.get("type")
            if t == "user":
                user_n += 1
                parsed = _parse_args(_user_text(rec))
                if parsed:
                    mode, target = parsed
                    invocs.append({
                        "session_id": path.stem,
                        "invoked_at": ts,
                        "mode": mode,
                        "target": target,
                        "git_branch": rec.get("gitBranch"),
                        "_user_at_start": user_n,
                        "_tool_at_start": tool_n,
                    })
            elif t == "assistant":
                msg = rec.get("message", {})
                for blk in msg.get("content", []) or []:
                    if isinstance(blk, dict) and blk.get("type") == "tool_use":
                        tool_n += 1
    out: list[dict] = []
    for i, inv in enumerate(invocs):
        if i + 1 < len(invocs):
            nxt = invocs[i + 1]
            end_ts, end_u, end_t = nxt["invoked_at"], nxt["_user_at_start"], nxt["_tool_at_start"]
        else:
            end_ts, end_u, end_t = last_ts or inv["invoked_at"], user_n, tool_n
        out.append({
            "session_id": inv["session_id"],
            "invoked_at": inv["invoked_at"],
            "ended_at": end_ts,
            "mode": inv["mode"],
            "target": inv["target"],
            "messages_count": end_u - inv["_user_at_start"],
            "tool_calls_count": end_t - inv["_tool_at_start"],
            "git_branch": inv["git_branch"],
        })
    return out


def compute_source_state() -> str:
    h = hashlib.sha256()
    for f in _session_files():
        h.update(f.name.encode()); h.update(b"\0")
        h.update(hashlib.sha256(f.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32]


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
    out: list[dict] = []
    for f in _session_files():
        for value in _walk_session(f):
            out.append(dp.make_data_point(
                collector_id=COLLECTOR_ID, kind=KIND,
                value=value, source_state=source_state,
                collector_pointer=cp,
            ))
    out.sort(key=lambda d: d["value"]["invoked_at"])
    return out


def verify(data_point: dict) -> tuple[str, str]:
    sess = data_point["value"]["session_id"]
    path = SESSIONS_DIR / f"{sess}.jsonl"
    if not path.is_file():
        return "dangling", "session_removed"
    current = _walk_session(path)
    invoked = data_point["value"]["invoked_at"]
    for v in current:
        if v["invoked_at"] == invoked:
            if v == data_point["value"]:
                return "live", "match"
            return "dangling", "value_drift"
    return "dangling", "invocation_not_found"


# ---- rendering -------------------------------------------------------

def _render_summary(points: list[dict]) -> str:
    if not points:
        return "# Cook events\n\n_No /cook invocations found in session transcripts._"
    by_mode: dict[str, int] = {}
    by_target: dict[str, int] = {}
    msgs: list[int] = []
    tools: list[int] = []
    for p in points:
        v = p["value"]
        by_mode[v["mode"]] = by_mode.get(v["mode"], 0) + 1
        tgt = v["target"] or "_free-hunt_"
        by_target[tgt] = by_target.get(tgt, 0) + 1
        msgs.append(v["messages_count"])
        tools.append(v["tool_calls_count"])
    lines = [
        "# Cook events — aggregate over all session transcripts",
        "",
        f"**total cooks**: {len(points)}",
        f"**span**: {points[0]['value']['invoked_at']} → {points[-1]['value']['invoked_at']}",
        "",
        "## Mode mix",
        "",
        "| mode | count |",
        "| --- | --: |",
    ]
    for m, n in sorted(by_mode.items(), key=lambda kv: -kv[1]):
        lines.append(f"| `{m}` | {n} |")
    lines += ["", "## Target frequency (top 10)", "", "| target | cooks |", "| --- | --: |"]
    for tgt, n in sorted(by_target.items(), key=lambda kv: -kv[1])[:10]:
        lines.append(f"| `{tgt}` | {n} |")
    lines += ["", "## Volume distribution", ""]
    if msgs:
        lines.append(f"messages_count: min={min(msgs)} median={sorted(msgs)[len(msgs)//2]} max={max(msgs)}")
        lines.append(f"tool_calls_count: min={min(tools)} median={sorted(tools)[len(tools)//2]} max={max(tools)}")
    lines += ["", "## Recent cooks", "", "| invoked_at | mode | target | msgs | tools | session |",
              "| --- | --- | --- | --: | --: | --- |"]
    for p in points[-10:][::-1]:
        v = p["value"]
        lines.append(
            f"| {v['invoked_at'][:19]} | `{v['mode']}` | "
            f"`{v['target'] or '—'}` | {v['messages_count']} | {v['tool_calls_count']} | "
            f"`{v['session_id'][:8]}` |"
        )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", action="store_true",
                    help="emit data points as jsonl instead of a summary")
    args = ap.parse_args()

    source_state = compute_source_state()
    points = collect(source_state)

    if args.jsonl:
        for p in points:
            sys.stdout.write(json.dumps(p, sort_keys=True) + "\n")
    else:
        print(_render_summary(points))
        print(f"\nsource_state: {source_state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
