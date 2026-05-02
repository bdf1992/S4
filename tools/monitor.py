"""Read-only monitoring rollup for the experiment.

Usage:
  python -m tools.monitor
  python -m tools.monitor --watch 300

The monitor does not persist snapshots and does not modify source. It
summarizes the existing dashboard substrate, then runs the current
deterministic validators/verifiers as subprocess checks. In watch mode,
failed checks are reported but do not stop polling; validation failures
are state, not a reason to stop observation.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


CHECKS = [
    ("debts", [sys.executable, "-m", "debts.validate"]),
    ("claim_audit", [sys.executable, "-m", "skills.claim_audit.verify"]),
    ("regime_audit", [sys.executable, "-m", "skills.regime_audit.verify"]),
]


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout.strip()


def _git_status() -> str:
    code, out = _run(["git", "status", "--short", "--branch"])
    return out if code == 0 else f"(git status failed: {out})"


def _snapshot_summary() -> tuple[list[str], int]:
    sys.path.insert(0, str(REPO_ROOT))
    from skills.dashboard import snapshot  # noqa: WPS433

    snap = snapshot.gather()
    audit = snap.get("audit", {})
    boards = snap.get("boards", {})
    leashes = snap.get("leashes", {})

    lines = [
        "# monitor",
        "",
        "## dashboard",
        f"- latest_bundle: {audit.get('latest_bundle_id')}",
        f"- floor_ratio: {audit.get('latest_floor_ratio')}",
        f"- audit_bundles: {audit.get('bundle_count')}",
    ]

    issues = 0
    missing_bedrock = [
        path for path, obs in snap.get("bedrock", {}).items()
        if not obs.get("exists")
    ]
    if missing_bedrock:
        issues += len(missing_bedrock)
        lines.append(f"- missing_bedrock: {', '.join(missing_bedrock)}")

    lines.append("")
    lines.append("## boards")
    for name in sorted(boards):
        board = boards[name]
        lb_open = board.get("load_bearing_open", 0)
        if lb_open:
            issues += lb_open
        lines.append(
            f"- {name}: {board.get('open', 0)} open, "
            f"{lb_open} load-bearing-open, {board.get('total', 0)} total"
        )

    lines.append("")
    lines.append("## leashes")
    for name in sorted(leashes):
        leash = leashes[name]
        lines.append(
            f"- {name}: {leash.get('state')}, "
            f"{leash.get('proposed', 0)} proposed, "
            f"{leash.get('promoted', 0)} promoted, "
            f"{leash.get('outputs', 0)} output bundles"
        )
    return lines, issues


def _check_summary() -> tuple[list[str], int]:
    lines = ["", "## checks"]
    failures = 0
    for name, cmd in CHECKS:
        code, out = _run(cmd)
        status = "OK" if code == 0 else f"FAIL exit={code}"
        if code != 0:
            failures += 1
        first_line = out.splitlines()[0] if out else "(no output)"
        lines.append(f"- {name}: {status} - {first_line}")
    return lines, failures


def run_once() -> int:
    lines, issue_count = _snapshot_summary()
    check_lines, failures = _check_summary()
    lines.extend(check_lines)
    lines.append("")
    lines.append("## git")
    lines.extend(f"  {line}" for line in _git_status().splitlines())
    lines.append("")
    lines.append(f"monitor_status: {'FAIL' if failures else 'OK'}")
    if issue_count:
        lines.append(f"attention_items: {issue_count}")
    print("\n".join(lines))
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--watch",
        type=int,
        metavar="SECONDS",
        help="repeat the monitor every N seconds until interrupted",
    )
    args = parser.parse_args()

    if not args.watch:
        return run_once()
    while True:
        run_once()
        sys.stdout.flush()
        time.sleep(args.watch)
        print("\n---\n")


if __name__ == "__main__":
    raise SystemExit(main())
