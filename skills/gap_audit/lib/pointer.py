"""Foundation 3 — pointer schema, construction, resolver registry.

A pointer is a structured record. Resolution is a function call into the
resolver registered for that pointer's `kind`. There is exactly one
resolver per kind.

Vendored from skills/claim_audit/lib/pointer.py at gap_audit creation
time, per the each-skill-carries-its-own-lib convention.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Callable

POINTER_FIELDS = (
    "kind", "target", "resolver",
    "bound_at.source_state", "bound_at.resolved_at",
    "last_status", "last_payload", "last_reason",
)

VALID_STATUSES = ("live", "dangling", "unresolved")


def make_unresolved(*, kind: str, target: Any, resolver: str) -> dict:
    return {
        "kind": kind,
        "target": target,
        "resolver": resolver,
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved",
        "last_payload": None,
        "last_reason": None,
    }


def validate_pointer(p: dict) -> tuple[bool, str]:
    if not isinstance(p, dict):
        return False, "not_a_record"
    for field in ("kind", "target", "resolver", "bound_at",
                  "last_status", "last_payload", "last_reason"):
        if field not in p:
            return False, f"missing_field:{field}"
    if not isinstance(p["bound_at"], dict):
        return False, "bound_at_not_record"
    for sub in ("source_state", "resolved_at"):
        if sub not in p["bound_at"]:
            return False, f"missing_field:bound_at.{sub}"
    if p["last_status"] not in VALID_STATUSES:
        return False, f"bad_status:{p['last_status']}"
    return True, "ok"


_REGISTRY: dict[str, Callable[[Any, str], tuple[str, Any]]] = {}


def register(kind: str, fn: Callable[[Any, str], tuple[str, Any]]) -> None:
    if kind in _REGISTRY:
        raise RuntimeError(f"resolver already registered for kind={kind}")
    _REGISTRY[kind] = fn


def registered_kinds() -> list[str]:
    return sorted(_REGISTRY.keys())


def resolve(pointer: dict, source_state: str) -> dict:
    kind = pointer["kind"]
    fn = _REGISTRY.get(kind)
    if fn is None:
        return {
            **pointer,
            "bound_at": {
                "source_state": source_state,
                "resolved_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            },
            "last_status": "dangling",
            "last_payload": None,
            "last_reason": f"no_resolver_for_kind:{kind}",
        }
    status, payload_or_reason = fn(pointer["target"], source_state)
    if status == "live":
        return {
            **pointer,
            "bound_at": {
                "source_state": source_state,
                "resolved_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            },
            "last_status": "live",
            "last_payload": payload_or_reason,
            "last_reason": None,
        }
    return {
        **pointer,
        "bound_at": {
            "source_state": source_state,
            "resolved_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        },
        "last_status": "dangling",
        "last_payload": None,
        "last_reason": str(payload_or_reason),
    }
