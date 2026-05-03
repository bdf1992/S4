"""Foundation 1 collector — joins cook events to git commits in their window.

cook_event tells you a cook *happened*. cook_outcome tells you what
the cook actually *produced*. Together they form the substrate a 2.0
signal can read to fire on anomaly: zero-commits cook (talk-only),
zero-net-loc cook, untouched-skill cook, fresh-target cook. Without
the outcome layer, the operator can see cadence + size but cannot
distinguish "ran 64 messages and produced nothing" from "ran 64
messages and shipped a graduated skill."

Source walked:
  - session jsonls (via tools.cook_event for the cook windows)
  - git log over the entire repo history (committer timestamp + numstat)

For each cook (session_id + invoked_at, from cook_event), finds every
commit whose committer timestamp falls inside [invoked_at, ended_at]
and aggregates the diff stats. Commit timestamps are normalized to
UTC seconds-since-epoch for the window comparison; the values
themselves carry the original ISO strings.

Run:
  python -m tools.cook_outcome           # joined-view summary
  python -m tools.cook_outcome --jsonl   # data points to stdout

See: foundations/data-point.md, foundations/collection-program.md.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from boards.lib import data_point as dp
from tools import cook_event

COLLECTOR_ID = "cook_outcome"
KIND = "cook_outcome"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["session_id", "invoked_at", "ended_at", "mode", "target",
                 "commits_count", "first_sha", "last_sha", "files_changed",
                 "insertions", "deletions", "net_loc", "skills_touched"],
    "properties": {
        "session_id": {"type": "string"},
        "invoked_at": {"type": "string"},
        "ended_at": {"type": "string"},
        "mode": {"enum": ["solve", "concept"]},
        "target": {"type": ["string", "null"]},
        "commits_count": {"type": "integer"},
        "first_sha": {"type": ["string", "null"]},
        "last_sha": {"type": ["string", "null"]},
        "files_changed": {"type": "integer"},
        "insertions": {"type": "integer"},
        "deletions": {"type": "integer"},
        "net_loc": {"type": "integer"},
        "skills_touched": {"type": "array", "items": {"type": "string"}},
    },
}

REPO = Path(__file__).resolve().parents[1]
INPUTS = list(cook_event.INPUTS) + [str(REPO / ".git")]


def _iso_to_utc_seconds(iso: str) -> int:
    """Parse ISO-8601 with timezone, return integer UTC seconds.
    Used for window comparison only; not a wall-clock read."""
    return int(_dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def _git_log() -> list[dict]:
    """Returns commits oldest→newest. Each: {sha, iso, ts, insertions, deletions, paths}."""
    res = subprocess.run(
        ["git", "log", "--pretty=format:__C__%H %cI", "--numstat", "--no-renames"],
        cwd=str(REPO), capture_output=True, text=True, check=True,
    )
    commits: list[dict] = []
    cur: dict | None = None
    for line in res.stdout.splitlines():
        if line.startswith("__C__"):
            if cur is not None:
                commits.append(cur)
            sha, iso = line[5:].split(" ", 1)
            cur = {"sha": sha[:8], "iso": iso,
                   "ts": _iso_to_utc_seconds(iso),
                   "insertions": 0, "deletions": 0, "paths": []}
        elif "\t" in line and cur is not None:
            parts = line.split("\t", 2)
            if len(parts) == 3:
                ins, dele, path = parts
                try:
                    cur["insertions"] += int(ins)
                except ValueError:
                    pass
                try:
                    cur["deletions"] += int(dele)
                except ValueError:
                    pass
                cur["paths"].append(path)
    if cur is not None:
        commits.append(cur)
    commits.reverse()
    return commits


def _skills_in_paths(paths: list[str]) -> list[str]:
    out: set[str] = set()
    for p in paths:
        parts = p.split("/")
        if len(parts) >= 2 and parts[0] == "skills":
            out.add(parts[1])
    return sorted(out)


def compute_source_state() -> str:
    h = hashlib.sha256()
    h.update(cook_event.compute_source_state().encode())
    h.update(b"\0")
    res = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO),
        capture_output=True, text=True, check=True,
    )
    h.update(res.stdout.strip().encode())
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
    cooks = cook_event.collect(cook_event.compute_source_state())
    commits = _git_log()
    cp = _collector_pointer()
    out: list[dict] = []
    for cpt in cooks:
        cv = cpt["value"]
        s = _iso_to_utc_seconds(cv["invoked_at"])
        e = _iso_to_utc_seconds(cv["ended_at"]) if cv["ended_at"] else s
        in_win = [c for c in commits if s <= c["ts"] <= e]
        files = sum(len(c["paths"]) for c in in_win)
        ins = sum(c["insertions"] for c in in_win)
        dele = sum(c["deletions"] for c in in_win)
        all_paths: list[str] = []
        for c in in_win:
            all_paths.extend(c["paths"])
        value = {
            "session_id": cv["session_id"],
            "invoked_at": cv["invoked_at"],
            "ended_at": cv["ended_at"],
            "mode": cv["mode"],
            "target": cv["target"],
            "commits_count": len(in_win),
            "first_sha": in_win[0]["sha"] if in_win else None,
            "last_sha": in_win[-1]["sha"] if in_win else None,
            "files_changed": files,
            "insertions": ins,
            "deletions": dele,
            "net_loc": ins - dele,
            "skills_touched": _skills_in_paths(all_paths),
        }
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND,
            value=value, source_state=source_state,
            collector_pointer=cp,
        ))
    out.sort(key=lambda d: d["value"]["invoked_at"])
    return out


def verify(data_point: dict) -> tuple[str, str]:
    cooks = cook_event.collect(cook_event.compute_source_state())
    invoked = data_point["value"]["invoked_at"]
    sess = data_point["value"]["session_id"]
    if not any(c["value"]["session_id"] == sess and c["value"]["invoked_at"] == invoked
               for c in cooks):
        return "dangling", "cook_invocation_not_found"
    current = collect(data_point["provenance"]["source_state"])
    for p in current:
        if (p["value"]["session_id"] == sess and
                p["value"]["invoked_at"] == invoked):
            if p["value"] == data_point["value"]:
                return "live", "match"
            return "dangling", "outcome_drift"
    return "dangling", "join_lost"


# ---- rendering -------------------------------------------------------

def _flag_anomalies(v: dict) -> list[str]:
    """Names anomaly flags this cook trips. Plain rules; not a 2.0 model."""
    flags = []
    if v["commits_count"] == 0:
        flags.append("no-commit")
    if v["commits_count"] > 0 and v["net_loc"] == 0:
        flags.append("net-zero")
    if v["commits_count"] > 0 and v["files_changed"] >= 50:
        flags.append("wide-blast")
    return flags


def _render(points: list[dict], scope_hint: str | None = None) -> str:
    if not points:
        return "# Cook outcomes\n\n_No cook events to join._"
    heading = "# Cook outcomes — cook events × git window"
    if scope_hint:
        heading += f"  ({scope_hint})"
    lines = [
        heading,
        "",
        "Per-cook diff stats from git commits whose committer timestamp falls inside",
        "the cook's session window. `flags` names anomalies a 2.0 signal would fire on.",
        "",
        "| invoked_at | mode | target | commits | files | net_loc | skills_touched | flags |",
        "| --- | --- | --- | --: | --: | --: | --- | --- |",
    ]
    no_commit = net_zero = total_net = 0
    for p in points:
        v = p["value"]
        flags = _flag_anomalies(v)
        if "no-commit" in flags: no_commit += 1
        if "net-zero" in flags: net_zero += 1
        total_net += v["net_loc"]
        sk = ", ".join(v["skills_touched"][:3])
        if len(v["skills_touched"]) > 3:
            sk += f" +{len(v['skills_touched']) - 3}"
        sk = sk or "—"
        lines.append(
            f"| {v['invoked_at'][:19]} | `{v['mode']}` | "
            f"`{v['target'] or '—'}` | {v['commits_count']} | "
            f"{v['files_changed']} | {v['net_loc']:+d} | {sk} | "
            f"{', '.join(flags) or '—'} |"
        )
    lines += [
        "",
        f"**totals**: {len(points)} cooks · "
        f"{no_commit} no-commit · {net_zero} net-zero · "
        f"net_loc cumulative = {total_net:+d}",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", action="store_true",
                    help="emit data points as jsonl instead of summary")
    ap.add_argument("--recent", type=int, default=None, metavar="N",
                    help="restrict the table and totals to the most recent N cooks "
                         "(default: all cooks)")
    args = ap.parse_args()

    ss = compute_source_state()
    points = collect(ss)

    scope_hint = None
    if args.recent is not None and args.recent > 0:
        if len(points) > args.recent:
            scope_hint = f"most recent {args.recent} of {len(points)}"
        points = points[-args.recent:]

    if args.jsonl:
        for p in points:
            sys.stdout.write(json.dumps(p, sort_keys=True) + "\n")
    else:
        print(_render(points, scope_hint=scope_hint))
        print(f"\nsource_state: {ss}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
