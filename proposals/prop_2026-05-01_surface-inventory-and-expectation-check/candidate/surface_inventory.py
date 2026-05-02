"""Walks repo artifacts and emits one surface_inventory_entry data
point per inspectable object — the unified inventory the deficit-
surface composition needs to compose against. Where surface_handwalk_
recurrence detects pressure on un-leashed surfaces (recurrence-as-
signal), surface_inventory enumerates every artifact regardless of
pressure, so downstream collectors and 3.0 orchestrations have a
single inventory to join against.

Per-artifact-kind rules:
  - proposals/prop_*/proposal.json present, decision_record_pointer
    null  -> graduation_state="candidate"
  - proposals/prop_*/proposal.json with decision_record_pointer set
    -> graduation_state="graduated"
  - skills/<skill>/   -> graduation_state="graduated" (presence implies
    promotion; archived skills handled via marker file, not yet
    formalized — they fall through to "unknown")
  - foundations/*.md  -> graduation_state="graduated" (immutable
    bedrock; modification is itself a 4.0 grading event)
  - meeting-notes/*.md -> graduation_state="unknown"

declared_expectation_kinds names value_schema kinds that downstream
verifiers emit for this artifact_kind. An empty list = inert surface
(no expectations declared yet). The list lives as a small per-kind
table inside this collector for now; future iterations may move it to
a separate data-point-producing collector so the table itself is data,
not authored prose.

This collector is itself 0.1: deterministic, no LLM, declared inputs.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

COLLECTOR_ID = "surface_inventory"
KIND = "surface_inventory_entry"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["path", "artifact_kind", "graduation_state",
                 "declared_expectation_kinds"],
    "properties": {
        "path": {"type": "string"},
        "artifact_kind": {"enum": ["proposal", "skill", "foundation",
                                    "meeting_note", "other"]},
        "graduation_state": {"enum": ["candidate", "graduated",
                                       "archived", "unknown"]},
        "declared_expectation_kinds": {"type": "array",
                                        "items": {"type": "string"}},
    },
    "additionalProperties": False,
}
INPUTS = ["proposals/prop_*", "skills/*", "foundations/*.md",
          "meeting-notes/*.md"]

_EXPECTATIONS = {
    "proposal": ["bundle_self_check"],
    "skill": ["bundle_self_check"],
    "foundation": [],
    "meeting_note": [],
    "other": [],
}


def _cp() -> dict:
    return {"kind": "collector",
            "target": {"collector_id": COLLECTOR_ID},
            "resolver": "collector_resolver",
            "bound_at": {"source_state": None, "resolved_at": None},
            "last_status": "unresolved",
            "last_payload": None, "last_reason": None}


def _make(value: Any, source_state: str, cp: dict) -> dict:
    canon = json.dumps(value, sort_keys=True,
                       separators=(",", ":")).encode()
    h = hashlib.sha256(canon).hexdigest()[:16]
    iso = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    return {"id": f"{COLLECTOR_ID}:{h}", "kind": KIND, "value": value,
            "provenance": {"collector": cp, "source_state": source_state,
                           "collected_at": iso}, "witness": h}


def _proposal_state(d: Path) -> str:
    pj = d / "proposal.json"
    if not pj.is_file():
        return "unknown"
    try:
        data = json.loads(pj.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "unknown"
    return ("graduated" if data.get("decision_record_pointer")
            else "candidate")


def _walk() -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    p_root = REPO_ROOT / "proposals"
    if p_root.is_dir():
        for d in sorted(p_root.iterdir()):
            if d.is_dir() and d.name.startswith("prop_"):
                rel = d.relative_to(REPO_ROOT).as_posix()
                out.append((rel, "proposal", _proposal_state(d)))
    s_root = REPO_ROOT / "skills"
    if s_root.is_dir():
        for d in sorted(s_root.iterdir()):
            if d.is_dir():
                rel = d.relative_to(REPO_ROOT).as_posix()
                out.append((rel, "skill", "graduated"))
    f_root = REPO_ROOT / "foundations"
    if f_root.is_dir():
        for f in sorted(f_root.glob("*.md")):
            rel = f.relative_to(REPO_ROOT).as_posix()
            out.append((rel, "foundation", "graduated"))
    n_root = REPO_ROOT / "meeting-notes"
    if n_root.is_dir():
        for f in sorted(n_root.glob("*.md")):
            rel = f.relative_to(REPO_ROOT).as_posix()
            out.append((rel, "meeting_note", "unknown"))
    return out


def compute_source_state() -> str:
    h = hashlib.sha256()
    for rel, kind_, state in _walk():
        h.update(f"{rel}|{kind_}|{state}".encode())
        h.update(b"\0")
    return "sha256:" + h.hexdigest()


def collect(source_state: str) -> list[dict]:
    cp = _cp()
    return [_make({"path": rel, "artifact_kind": k,
                   "graduation_state": state,
                   "declared_expectation_kinds": _EXPECTATIONS.get(k, [])},
                  source_state, cp)
            for rel, k, state in _walk()]


def verify(data_point: dict) -> tuple[str, str]:
    rel = data_point["value"]["path"]
    if not (REPO_ROOT / rel).exists():
        return "dangling", "path_no_longer_present"
    return "live", "path_present"
