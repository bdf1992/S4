"""Standup / scrum composer — operator-facing ritual on existing collectors.

Two modes. Both compose existing 1.0 collectors into one markdown
artifact for operator consumption. Neither mode invents a new
measurement; both are pure source-walks over what other collectors
already emit.

  - **standup** (default window 24h) — "what's live right now and
    what shifted recently." Headline floor state, commits + cook
    outcomes inside the window, uncommitted-tree summary, open
    proposals, verify-check failures, decisions landed in window.
  - **scrum** (default window 7d) — standup-shape PLUS the iteration
    lens: per-cook outcome table, ranked next-target candidates from
    floor_growth, per-skill substrate × peer status. The same shape
    operator hand-authored once at approvals/books_close_2026-05-01.md
    when no skill existed; this is the recurring version.

Per meeting-notes/meeting-schedule.md the project is event-driven, not
calendar-driven. This composer is invoked by the operator (via /standup
or /scrum slash shims under .claude/skills/) — not on a clock. It is
the slash-command analog of the books-close digest, on top of the
collectors that have landed since.

Source walked:
  - tools.cook_outcome (cooks × git commits in window)
  - tools.floor_growth (peer consumption per skill, ranked candidates)
  - skills.regime_audit.collectors.regime_classification + signal
    (floor_ratio + by_regime, fit on current source)
  - approvals/decisions.jsonl (decisions in window)
  - proposals/<slug>/proposal.json (open proposals)
  - meeting-notes/YYYY-MM-DD-*.md (recent notes by filename date)
  - git log + git status --short --branch
  - tools.monitor CHECKS (verifier exit codes)

Run:
  python -m tools.standup
  python -m tools.standup --mode scrum
  python -m tools.standup --since 48h
  python -m tools.standup --since 2026-05-01T00:00:00+00:00
  python -m tools.standup --out approvals/standup_2026-05-03.md
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from skills.regime_audit.collectors import regime_classification as _ra_collect  # noqa: E402
from skills.regime_audit.signals import regime_distribution as _ra_signal  # noqa: E402
from tools import cook_outcome as _co  # noqa: E402
from tools import floor_growth as _fg  # noqa: E402
from tools import monitor as _mon  # noqa: E402

DEFAULT_WINDOWS = {"standup": "24h", "scrum": "7d"}
RELATIVE_RE = re.compile(r"^(\d+)([hd])$")


def _parse_since(spec: str, now: _dt.datetime) -> _dt.datetime:
    """Accept '24h', '7d', or an ISO-8601 string with timezone."""
    m = RELATIVE_RE.match(spec)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = _dt.timedelta(hours=n) if unit == "h" else _dt.timedelta(days=n)
        return now - delta
    return _dt.datetime.fromisoformat(spec.replace("Z", "+00:00"))


def _commits_in_window(since: _dt.datetime, until: _dt.datetime) -> list[dict]:
    fmt = "%H%x09%cI%x09%s"
    res = subprocess.run(
        ["git", "log", f"--pretty=format:{fmt}", "--no-merges",
         f"--since={since.isoformat()}", f"--until={until.isoformat()}"],
        cwd=str(REPO), capture_output=True, text=True, check=True,
    )
    out = []
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        if len(parts) == 3:
            sha, iso, subject = parts
            out.append({"sha": sha[:8], "iso": iso, "subject": subject})
    return out


def _git_status_short() -> tuple[str, list[str]]:
    res = subprocess.run(
        ["git", "status", "--short", "--branch"],
        cwd=str(REPO), capture_output=True, text=True, check=True,
    )
    lines = res.stdout.splitlines()
    raw = lines[0] if lines else ""
    # `## master`, `## master...origin/master`, `## master [ahead 2]`
    branch = raw[3:].split("...", 1)[0].split(" ", 1)[0] if raw.startswith("## ") else raw
    return branch, lines[1:]


def _cook_outcomes_in_window(since: _dt.datetime, until: _dt.datetime) -> list[dict]:
    ss = _co.compute_source_state()
    points = _co.collect(ss)
    s_ts, u_ts = since.timestamp(), until.timestamp()
    out = []
    for p in points:
        invoked_iso = p["value"]["invoked_at"]
        try:
            invoked_ts = _dt.datetime.fromisoformat(
                invoked_iso.replace("Z", "+00:00")
            ).timestamp()
        except ValueError:
            continue
        if s_ts <= invoked_ts <= u_ts:
            out.append(p["value"])
    return out


def _floor_signal() -> dict:
    ss = _ra_collect.compute_source_state()
    rows = _ra_collect.collect(ss)
    fitted = _ra_signal.fit(rows)
    fitted["source_state"] = ss
    return fitted


def _open_proposals() -> list[dict]:
    """Walk proposals/<slug>/proposal.json, return ones not in decisions."""
    decided = set()
    dec_path = REPO / "approvals" / "decisions.jsonl"
    if dec_path.is_file():
        for line in dec_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("verdict") in ("promote", "reject"):
                pid = rec.get("proposal_id")
                if pid:
                    decided.add(pid)
    out = []
    prop_dir = REPO / "proposals"
    if not prop_dir.is_dir():
        return out
    for d in sorted(prop_dir.iterdir()):
        if not d.is_dir():
            continue
        manifest = d / "proposal.json"
        if not manifest.is_file():
            continue
        try:
            prop = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        pid = prop.get("proposal_id")
        if pid and pid not in decided:
            out.append({
                "proposal_id": pid,
                "target": prop.get("target", "?"),
                "claimed_kind": prop.get("claimed_kind", "?"),
                "dir": d.name,
            })
    return out


def _decisions_in_window(since: _dt.datetime, until: _dt.datetime) -> list[dict]:
    out = []
    dec_path = REPO / "approvals" / "decisions.jsonl"
    if not dec_path.is_file():
        return out
    s_ts, u_ts = since.timestamp(), until.timestamp()
    for line in dec_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        decided_at = rec.get("decided_at")
        if not decided_at:
            continue
        try:
            ts = _dt.datetime.fromisoformat(
                decided_at.replace("Z", "+00:00")
            ).timestamp()
        except ValueError:
            continue
        if s_ts <= ts <= u_ts:
            out.append(rec)
    return out


def _meeting_notes_in_window(since: _dt.datetime) -> list[str]:
    """Returns filenames of dated notes whose date >= since (date only)."""
    out = []
    nd = REPO / "meeting-notes"
    if not nd.is_dir():
        return out
    cutoff = since.date()
    for p in sorted(nd.glob("*.md")):
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", p.name)
        if not m:
            continue
        try:
            note_date = _dt.date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if note_date >= cutoff:
            out.append(p.name)
    return out


def _verify_check_summary() -> list[tuple[str, int, str]]:
    """Run monitor's CHECKS once; return [(name, exit_code, first_line)]."""
    out = []
    for name, cmd in _mon.CHECKS:
        code, stdout = _mon._run(cmd)
        first = stdout.splitlines()[0] if stdout else "(no output)"
        out.append((name, code, first))
    return out


# ---- rendering -------------------------------------------------------

def _fmt_window(since: _dt.datetime, until: _dt.datetime) -> str:
    return f"{since.isoformat(timespec='minutes')} → {until.isoformat(timespec='minutes')}"


def _render_headline(mode: str, since: _dt.datetime, until: _dt.datetime,
                     branch: str, dirty: list[str], floor: dict) -> list[str]:
    return [
        f"# {mode.capitalize()} — {until.date().isoformat()}",
        "",
        f"**Mode:** `{mode}`  ·  **Window:** {_fmt_window(since, until)}  ·  "
        f"**Branch:** `{branch}`",
        "",
        f"- floor_ratio (0.1+0.2)/0.3: **{floor['floor_ratio']:.2f}**  "
        f"(total artifacts walked: {floor['total']})",
        f"- working tree: **{len(dirty)}** dirty file(s)",
        "",
    ]


def _render_shipped(commits: list[dict], cooks: list[dict]) -> list[str]:
    lines = ["## Shipped (in window)", ""]
    if not commits and not cooks:
        lines.append("_No commits and no cook events fell inside the window._")
        lines.append("")
        return lines
    if commits:
        lines.append(f"**{len(commits)} commit(s):**")
        lines.append("")
        for c in commits[:20]:
            lines.append(f"- `{c['sha']}` {c['iso'][:19]} — {c['subject']}")
        if len(commits) > 20:
            lines.append(f"- _…+{len(commits) - 20} more_")
        lines.append("")
    if cooks:
        landed = [c for c in cooks if c["commits_count"] > 0]
        no_commit = [c for c in cooks if c["commits_count"] == 0]
        lines.append(
            f"**Cook events:** {len(cooks)} total · "
            f"{len(landed)} shipped · {len(no_commit)} no-commit (talk-only)"
        )
        lines.append("")
        if landed:
            lines.append("| invoked_at | mode | target | files | net_loc | skills |")
            lines.append("| --- | --- | --- | --: | --: | --- |")
            for cv in landed[-10:]:
                sk = ", ".join(cv["skills_touched"][:3])
                if len(cv["skills_touched"]) > 3:
                    sk += f" +{len(cv['skills_touched']) - 3}"
                sk = sk or "—"
                lines.append(
                    f"| {cv['invoked_at'][:19]} | `{cv['mode']}` | "
                    f"`{cv['target'] or '—'}` | {cv['files_changed']} | "
                    f"{cv['net_loc']:+d} | {sk} |"
                )
            lines.append("")
    return lines


def _render_in_flight(dirty: list[str], opens: list[dict]) -> list[str]:
    lines = ["## In flight", ""]
    if dirty:
        lines.append(f"**{len(dirty)} dirty file(s) in working tree:**")
        lines.append("")
        for d in dirty[:30]:
            lines.append(f"- `{d}`")
        if len(dirty) > 30:
            lines.append(f"- _…+{len(dirty) - 30} more_")
        lines.append("")
    if opens:
        lines.append(f"**{len(opens)} open proposal(s):**")
        lines.append("")
        for p in opens:
            lines.append(
                f"- `{p['proposal_id']}` — target `{p['target']}` · "
                f"kind `{p['claimed_kind']}` · "
                f"[`{p['dir']}`](../proposals/{p['dir']}/)"
            )
        lines.append("")
    if not dirty and not opens:
        lines.append("_Nothing uncommitted; no open proposals._")
        lines.append("")
    return lines


def _render_attention(checks: list[tuple[str, int, str]],
                      cooks: list[dict],
                      decisions: list[dict],
                      meetings: list[str]) -> list[str]:
    lines = ["## Wants attention", ""]
    failures = [(n, c, msg) for n, c, msg in checks if c != 0]
    no_commit = [c for c in cooks if c["commits_count"] == 0]
    something = bool(failures or no_commit or decisions or meetings)
    if not something:
        lines.append("_All verifier checks pass; no no-commit cooks; no decisions; no recent meeting notes._")
        lines.append("")
        return lines
    if failures:
        lines.append(f"**Verifier failures:** {len(failures)}")
        lines.append("")
        for n, code, msg in failures:
            lines.append(f"- `{n}` exit={code} — {msg}")
        lines.append("")
    if no_commit:
        lines.append(
            f"**No-commit cooks in window:** {len(no_commit)} "
            f"(receipts didn't land; cook discipline leak)"
        )
        lines.append("")
        for cv in no_commit[-6:]:
            lines.append(f"- {cv['invoked_at'][:19]} target `{cv['target'] or '—'}`")
        lines.append("")
    if decisions:
        lines.append(f"**Decisions landed:** {len(decisions)}")
        lines.append("")
        for r in decisions:
            v = r.get("verdict", "?")
            pid = r.get("proposal_id", "?")
            lines.append(f"- `{v}` `{pid}` at {r.get('decided_at', '?')[:19]}")
        lines.append("")
    if meetings:
        lines.append(f"**Recent meeting notes:** {len(meetings)}")
        lines.append("")
        for fn in meetings:
            lines.append(f"- [`{fn}`](../meeting-notes/{fn})")
        lines.append("")
    return lines


def _render_iteration_lens(floor: dict, fg_points: list[dict]) -> list[str]:
    """Scrum-only: regime distribution + ranked next-target candidates."""
    lines = ["## Iteration lens — floor + next-target candidates", ""]
    lines.append("### Regime distribution (current source)")
    lines.append("")
    lines.append("| regime | count |")
    lines.append("| --- | --: |")
    for k in ("bedrock", "0.0", "0.1", "0.2", "0.3", "unclassified"):
        if k in floor["by_regime"]:
            lines.append(f"| `{k}` | {floor['by_regime'][k]} |")
    lines.append("")
    ranked = _fg._ranked(fg_points)
    if not ranked:
        lines.append("_No floor-growth candidates surfaced — every skill is graduated or has no leverage rule fit._")
        lines.append("")
        return lines
    lines.append("### Next-target candidates (highest leverage first)")
    lines.append("")
    for rule_id, rule_text, names in ranked:
        lines.append(f"**{rule_id}** — {rule_text}")
        lines.append("")
        for n in names:
            lines.append(f"- `{n}`")
        lines.append("")
    return lines


def _collect_structured(mode: str, since: _dt.datetime,
                        until: _dt.datetime) -> dict:
    """Same source-walk as render(), emitting a structured dict instead of
    markdown. The dict is the contract surface heartbeat configs reference
    via {{ steps.<id>.<field> }} substitution. Schema at
    schemas/scrum_output.json."""
    branch, dirty = _git_status_short()
    floor = _floor_signal()
    commits = _commits_in_window(since, until)
    cooks = _cook_outcomes_in_window(since, until)
    opens = _open_proposals()
    decisions = _decisions_in_window(since, until)
    meetings = _meeting_notes_in_window(since)
    checks = _verify_check_summary()

    out = {
        "schema_version": "0.1",
        "mode": mode,
        "window": {"since_iso": since.isoformat(),
                   "until_iso": until.isoformat()},
        "branch": branch,
        "dirty_count": len(dirty),
        "dirty_files": dirty,
        "floor_ratio": floor["floor_ratio"],
        "floor_total": floor["total"],
        "by_regime": floor["by_regime"],
        "commits_count": len(commits),
        "commits": commits,
        "cooks_count": len(cooks),
        "cooks_landed": [c for c in cooks if c["commits_count"] > 0],
        "cooks_no_commit": [c for c in cooks if c["commits_count"] == 0],
        "open_proposals": opens,
        "decisions": decisions,
        "meeting_notes": meetings,
        "verifier_failures": [
            {"name": n, "exit": c, "first_line": m}
            for (n, c, m) in checks if c != 0
        ],
        "source_state": {
            "floor": floor["source_state"],
            "cook_outcome": _co.compute_source_state(),
        },
    }
    if mode == "scrum":
        ss_fg = _fg.compute_source_state()
        fg_points = _fg.collect(ss_fg)
        ranked = _fg._ranked(fg_points)
        out["next_targets"] = [
            {"rule_id": rid, "rule_text": rtxt, "skills": names}
            for (rid, rtxt, names) in ranked
        ]
        out["source_state"]["floor_growth"] = ss_fg
    return out


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO), capture_output=True, text=True, check=True,
    ).stdout.strip()


def _last_receipt(receipt_dir: Path) -> dict | None:
    """Return the most recent *.receipt.json under receipt_dir, or None."""
    if not receipt_dir.is_dir():
        return None
    receipts = sorted(receipt_dir.glob("*.receipt.json"))
    if not receipts:
        return None
    try:
        return json.loads(receipts[-1].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def heartbeat_gate(receipt_dir: str | Path,
                   state: dict | None = None) -> bool:
    """Default gate for scrum/standup heartbeats. Fires iff git HEAD has
    moved since the last receipt at receipt_dir, OR (bootstrap) no prior
    receipt exists. `state` is unused today; reserved for the runner to
    pass extra context.

    Closes GAP-14 from hand-play 002: receipt_dir is no longer hard-coded
    to scrum's directory, so multiple rituals can share this function and
    each walk their own receipts."""
    rd = Path(receipt_dir)
    if not rd.is_absolute():
        rd = REPO / rd
    last = _last_receipt(rd)
    if last is None:
        return True
    last_head = last.get("git_head_at_fire")
    if not last_head:
        return True
    return _git_head() != last_head


def heartbeat_idempotency_key(receipt_dir: str | Path,
                              state: dict | None = None) -> str:
    """Closed-form idempotency key: git HEAD (12 chars) + the timestamp of
    the most recent prior receipt at receipt_dir (or 'bootstrap' if none).
    Two ticks at the same HEAD with no intervening receipt collapse to
    one fire.

    Closes GAP-14 from hand-play 002: ritual-agnostic via receipt_dir."""
    rd = Path(receipt_dir)
    if not rd.is_absolute():
        rd = REPO / rd
    head = _git_head()
    last = _last_receipt(rd)
    last_iso = (last or {}).get("fired_at", "bootstrap")
    return f"{head[:12]}::{last_iso}"


def render(mode: str, since: _dt.datetime, until: _dt.datetime) -> str:
    branch, dirty = _git_status_short()
    floor = _floor_signal()
    commits = _commits_in_window(since, until)
    cooks = _cook_outcomes_in_window(since, until)
    opens = _open_proposals()
    decisions = _decisions_in_window(since, until)
    meetings = _meeting_notes_in_window(since)
    checks = _verify_check_summary()

    lines: list[str] = []
    lines += _render_headline(mode, since, until, branch, dirty, floor)
    lines += _render_shipped(commits, cooks)
    lines += _render_in_flight(dirty, opens)
    lines += _render_attention(checks, cooks, decisions, meetings)
    if mode == "scrum":
        ss_fg = _fg.compute_source_state()
        fg_points = _fg.collect(ss_fg)
        lines += _render_iteration_lens(floor, fg_points)
    lines += [
        "---",
        "",
        f"_floor source_state_: `{floor['source_state']}`  ",
        f"_cook_outcome source_state_: `{_co.compute_source_state()}`",
    ]
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Compose standup or scrum markdown from existing collectors.",
    )
    ap.add_argument("--mode", choices=("standup", "scrum"), default="standup")
    ap.add_argument(
        "--since", default=None,
        help="Window start: '24h', '7d', or ISO-8601. "
             "Defaults: standup=24h, scrum=7d.",
    )
    ap.add_argument(
        "--out", default=None,
        help="Write to this path instead of stdout.",
    )
    ap.add_argument(
        "--emit-structured", default=None,
        help="Also write a JSON sidecar (heartbeat output_writer surface) "
             "to this path. Schema: schemas/scrum_output.json.",
    )
    args = ap.parse_args()

    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)
    spec = args.since or DEFAULT_WINDOWS[args.mode]
    since = _parse_since(spec, now)
    md = render(args.mode, since, now)

    if args.out:
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = REPO / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
        print(f"wrote {out_path.relative_to(REPO)}")
    else:
        sys.stdout.write(md)

    if args.emit_structured:
        sp = Path(args.emit_structured)
        if not sp.is_absolute():
            sp = REPO / sp
        sp.parent.mkdir(parents=True, exist_ok=True)
        structured = _collect_structured(args.mode, since, now)
        sp.write_text(json.dumps(structured, indent=2, default=str),
                      encoding="utf-8")
        print(f"wrote {sp.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
