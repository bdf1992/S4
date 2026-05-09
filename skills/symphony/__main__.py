"""Subcommand dispatcher for the symphony lifecycle skill.

Usage:
    python -m skills.symphony new --title <title> --kind <kind>   # body via stdin
    python -m skills.symphony status
    python -m skills.symphony review <issue-number>
    python -m skills.symphony approve <issue-number>
    python -m skills.symphony reject <issue-number>
    python -m skills.symphony probe
"""
from __future__ import annotations

import argparse
import sys

from . import lifecycle


def _parse_int_or_die(s: str, label: str) -> int:
    try:
        return int(s)
    except ValueError:
        sys.stderr.write(f"symphony {label}: argument must be an integer issue number\n")
        sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(prog="symphony", add_help=False)
    parser.add_argument("subcommand", nargs="?")
    parser.add_argument("rest", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    sub = args.subcommand
    rest = args.rest
    if not sub or sub in ("-h", "--help"):
        sys.stdout.write(__doc__ or "")
        return 0
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
    if sub == "status":
        return lifecycle.status()
    if sub == "review":
        if not rest:
            sys.stderr.write("symphony review: missing issue number\n")
            return 2
        return lifecycle.review(_parse_int_or_die(rest[0], "review"))
    if sub == "approve":
        if not rest:
            sys.stderr.write("symphony approve: missing issue number\n")
            return 2
        return lifecycle.approve(_parse_int_or_die(rest[0], "approve"))
    if sub == "reject":
        if not rest:
            sys.stderr.write("symphony reject: missing issue number\n")
            return 2
        return lifecycle.reject(_parse_int_or_die(rest[0], "reject"))
    if sub == "probe":
        return lifecycle.probe()
    sys.stderr.write(f"symphony: unknown subcommand '{sub}'\n")
    sys.stdout.write(__doc__ or "")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
