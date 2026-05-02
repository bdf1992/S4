"""Fences the install-drift detection in factory_opportunities_cards._proposal_card.

The cope-code this replaces declared a proposal `promoted` whenever the
operator's decision verdict was `promote`, ignoring whether the candidate
was actually installed. That painted over a real drift case observed on
2026-05-02 with prop:2026-04-30:verifier-for-subprotocol-for-claude-code:
operator decision logged 2026-05-01, but the promoter never ran for two
days, and the board still claimed PROMOTED.

This script exercises the four lifecycle states directly. Exit 0 iff each
state produces the expected column + install_drift signal.

Usage:  python -m boards.collectors.test_factory_install_drift
"""
from __future__ import annotations

import sys

from boards.collectors.factory_opportunities_cards import _proposal_card


def _case(label, proposal, decision, want_column, want_drift):
    card = _proposal_card(proposal, decision)
    got_column = card["column"]
    got_drift = bool(card.get("payload", {}).get("install_drift"))
    if got_column != want_column or got_drift != want_drift:
        print(f"FAIL: {label}: column={got_column!r} drift={got_drift!r}; "
              f"want column={want_column!r} drift={want_drift!r}", file=sys.stderr)
        return False
    return True


def main() -> int:
    base = {"proposal_id": "prop:test:foo", "_source_path": "x", "gap_pointers": []}
    cases = [
        ("install_drift: promote-decision but manifest still proposed",
         {**base, "status": "proposed"}, {"verdict": "promote", "decided_at": "t"},
         "proposed", True),
        ("clean promote: promote-decision and manifest promoted",
         {**base, "status": "promoted"}, {"verdict": "promote", "decided_at": "t"},
         "promoted", False),
        ("reject: rejection always wins",
         {**base, "status": "proposed"}, {"verdict": "reject", "decided_at": "t"},
         "rejected", False),
        ("no decision: column stays proposed",
         {**base, "status": "proposed"}, None,
         "proposed", False),
        ("missing manifest status with promote-decision is also drift",
         {**base}, {"verdict": "promote", "decided_at": "t"},
         "proposed", True),
    ]
    ok = all(_case(*c) for c in cases)
    if ok:
        print(f"factory install_drift: {len(cases)}/{len(cases)} cases pass")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
