"""Subcommand dispatcher for the symphony lifecycle skill.

Usage:
    python -m skills.symphony new --title <title> --kind <kind>   # body via stdin
    python -m skills.symphony dispatch <issue-number>             # add symphony-doing, Status=In Progress, branch issue-N
    python -m skills.symphony mark-done <issue-number>            # add symphony-done, remove symphony-doing, Status=In Review; optional comment via stdin
    python -m skills.symphony pr <issue-number> --title <title>   # body via stdin; opens PR on issue-N branch
    python -m skills.symphony status
    python -m skills.symphony review <issue-number>
    python -m skills.symphony approve <issue-number> [--merge {squash,merge,rebase}]
    python -m skills.symphony bulk-approve <N1> <N2> ... [--merge {squash,merge,rebase}]
    python -m skills.symphony reject <issue-number> [--reason <text>]
    python -m skills.symphony probe
    python -m skills.symphony start                                                  # launch cc-symphony detached on :8080 with $GITHUB_TOKEN from gh keychain
    python -m skills.symphony stop                                                   # kill cc-symphony.exe
"""
from __future__ import annotations

import argparse
import sys

from . import lifecycle, process


def _parse_int_or_die(s: str, label: str) -> int:
    try:
        return int(s)
    except ValueError:
        sys.stderr.write(f"symphony {label}: argument must be an integer issue number\n")
        sys.exit(2)


def _read_optional_stdin() -> str:
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read()


def main() -> int:
    # Handle help before argparse — add_help=False on the dispatcher would
    # otherwise raise "unrecognized arguments: --help".
    if len(sys.argv) <= 1 or sys.argv[1] in ("-h", "--help", "help"):
        sys.stdout.write(__doc__ or "")
        return 0
    parser = argparse.ArgumentParser(prog="symphony", add_help=False)
    parser.add_argument("subcommand", nargs="?")
    parser.add_argument("rest", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    sub = args.subcommand
    rest = args.rest
    if sub == "new":
        new_parser = argparse.ArgumentParser(prog="symphony new")
        new_parser.add_argument("--title", required=True)
        new_parser.add_argument("--kind", required=True,
                                choices=["debt", "feature", "refactor"])
        new_args = new_parser.parse_args(rest)
        body = sys.stdin.read()
        if not body.strip():
            sys.stderr.write("symphony new: body must be supplied via stdin\n")
            return 2
        return lifecycle.new(new_args.title, new_args.kind, body)
    if sub == "dispatch":
        if not rest:
            sys.stderr.write("symphony dispatch: missing issue number\n")
            return 2
        return lifecycle.dispatch(_parse_int_or_die(rest[0], "dispatch"))
    if sub == "mark-done":
        if not rest:
            sys.stderr.write("symphony mark-done: missing issue number\n")
            return 2
        n = _parse_int_or_die(rest[0], "mark-done")
        comment = _read_optional_stdin()
        return lifecycle.mark_done(n, comment if comment.strip() else None)
    if sub == "pr":
        pr_parser = argparse.ArgumentParser(prog="symphony pr")
        pr_parser.add_argument("issue_number", type=int)
        pr_parser.add_argument("--title", required=True)
        pr_parser.add_argument("--base", default="master")
        pr_args = pr_parser.parse_args(rest)
        body = sys.stdin.read()
        if not body.strip():
            sys.stderr.write("symphony pr: body must be supplied via stdin\n")
            return 2
        return lifecycle.pr(pr_args.issue_number, pr_args.title, body, base=pr_args.base)
    if sub == "status":
        return lifecycle.status()
    if sub == "review":
        if not rest:
            sys.stderr.write("symphony review: missing issue number\n")
            return 2
        return lifecycle.review(_parse_int_or_die(rest[0], "review"))
    if sub == "approve":
        approve_parser = argparse.ArgumentParser(prog="symphony approve")
        approve_parser.add_argument("issue_number", type=int)
        approve_parser.add_argument("--merge", choices=["squash", "merge", "rebase"],
                                    default=None)
        approve_args = approve_parser.parse_args(rest)
        return lifecycle.approve(approve_args.issue_number, merge=approve_args.merge)
    if sub == "bulk-approve":
        bulk_parser = argparse.ArgumentParser(prog="symphony bulk-approve")
        bulk_parser.add_argument("issue_numbers", type=int, nargs="+")
        bulk_parser.add_argument("--merge", choices=["squash", "merge", "rebase"],
                                 default=None)
        bulk_args = bulk_parser.parse_args(rest)
        return lifecycle.bulk_approve(bulk_args.issue_numbers, merge=bulk_args.merge)
    if sub == "reject":
        reject_parser = argparse.ArgumentParser(prog="symphony reject")
        reject_parser.add_argument("issue_number", type=int)
        reject_parser.add_argument("--reason", default=None)
        reject_args = reject_parser.parse_args(rest)
        return lifecycle.reject(reject_args.issue_number, reason=reject_args.reason)
    if sub == "probe":
        return lifecycle.probe()
    if sub == "start":
        return process.start()
    if sub == "stop":
        return process.stop()
    sys.stderr.write(f"symphony: unknown subcommand '{sub}'\n")
    sys.stdout.write(__doc__ or "")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
