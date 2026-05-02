"""leash_state — operator-authored toggle for the leash.

The toggle has three states (CLAUDE.md:26):
  - "on": every candidate runs through every declared decision point.
  - "off": the leash is disengaged; candidates pass through with claim
    "unleashed" and no decision points are consulted.
  - "scoped": the leash is on for events listed in scoped_on_events,
    off for everything else.

Optional orthogonal field `vocal` (bool, default false): introduced
by leash_for_symphony per its proposal preview, lifted here once a
second leash (leash_for_cc_afk preview, 2026-04-30) needed the same
shape. State answers "does this leash gate?"; vocal answers "does
this leash narrate?". An off+vocal leash does not gate but still
emits full structured-event capture for post-hoc grading.

The state is operator-authored and lives in leash_state.json at the
skill root. It is NOT a 0.1 collected datum (there's no source to walk);
it is 0.1 *config* — a parameter the orchestration consults before
running its decision points. verify.py confirms the file's schema and
that orchestrate.py consults it before evaluate.
"""
from __future__ import annotations

import json
from pathlib import Path

VALID_STATES = ("on", "off", "scoped")
FILENAME = "leash_state.json"


def validate(state: dict) -> tuple[bool, str]:
    if not isinstance(state, dict):
        return False, "not_a_dict"
    if "state" not in state:
        return False, "missing_state_field"
    if state["state"] not in VALID_STATES:
        return False, f"invalid_state:{state['state']!r}"
    if state["state"] == "scoped":
        if "scoped_on_events" not in state:
            return False, "scoped_state_missing_scoped_on_events"
        if not isinstance(state["scoped_on_events"], list):
            return False, "scoped_on_events_not_list"
        if not all(isinstance(e, str) for e in state["scoped_on_events"]):
            return False, "scoped_on_events_contains_non_string"
    if "vocal" in state and not isinstance(state["vocal"], bool):
        return False, f"vocal_not_bool:{type(state['vocal']).__name__}"
    return True, ""


def is_vocal(d: dict) -> bool:
    """True iff `d` carries `vocal=true`. Polymorphic: accepts a
    validated leash_state dict, an orchestration outcome dict, or
    any other dict that carries the field forward."""
    return bool(d.get("vocal", False))


def read(skill_root: Path) -> dict:
    path = skill_root / FILENAME
    if not path.exists():
        raise FileNotFoundError(f"leash_state file missing: {path}")
    state = json.loads(path.read_text(encoding="utf-8"))
    ok, reason = validate(state)
    if not ok:
        raise ValueError(f"leash_state invalid: {reason}")
    return state


def is_leashed(state: dict, candidate: dict, key: str = "event") -> tuple[bool, str]:
    """Given a validated state and a candidate, return (leashed, reason).

    `key` selects which candidate field is matched against scoped_on_events.
    Defaults to "event" for the hooks leash; slash-commands and other leashes
    pass key="name" (or whatever their candidate's identity field is). See
    debts/D-005.json for the bug this parameter exists to close.
    """
    s = state["state"]
    if s == "on":
        return True, "state_on"
    if s == "off":
        return False, "state_off"
    value = candidate.get(key)
    if value in state.get("scoped_on_events", []):
        return True, f"scoped_on_{key}:{value}"
    return False, f"scoped_off_{key}:{value}"
