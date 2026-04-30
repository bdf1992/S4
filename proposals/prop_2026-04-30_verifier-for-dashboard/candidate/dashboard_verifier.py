"""Candidate verify.py for skills/dashboard — a 0.1 multi-entry-point
render skill (render / snapshot / narrate / html, all over the same
live source). Walks the four Python entry points + SKILL.md and emits
one bundle_self_check data point per file-level structural check.

Closes skill_without_verifier:21d380eb7bc25319. On promotion, this
file moves to skills/dashboard/verify.py.

Foundation-2 conformant: deterministic, no LLM, declared inputs,
audit budget under 80 lines. Helpers inlined for self-containment.
"""
from __future__ import annotations

import ast
import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_REL = "skills/dashboard"
PY_FILES = ("render.py", "snapshot.py", "narrate.py", "html.py")

COLLECTOR_ID = "dashboard_verifier"
KIND = "bundle_self_check"
VALUE_SCHEMA = {"type": "object", "required": ["check_id", "verdict", "reason"]}
INPUTS = [f"{SKILL_REL}/SKILL.md"] + [f"{SKILL_REL}/{f}" for f in PY_FILES]

_LLM_DENY = ("anthropic", "openai", "google.generativeai", "cohere")
_NONDET_DENY = ("random", "uuid", "secrets")


def _cp() -> dict:
    return {"kind": "collector", "target": {"collector_id": COLLECTOR_ID},
            "resolver": "collector_resolver",
            "bound_at": {"source_state": None, "resolved_at": None},
            "last_status": "unresolved", "last_payload": None, "last_reason": None}


def _make(value: Any, source_state: str, cp: dict) -> dict:
    canon = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    h = hashlib.sha256(canon).hexdigest()[:16]
    iso = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    return {"id": f"{COLLECTOR_ID}:{h}", "kind": KIND, "value": value,
            "provenance": {"collector": cp, "source_state": source_state,
                           "collected_at": iso}, "witness": h}


def _imports(rel: str) -> list[str] | None:
    p = REPO_ROOT / rel
    if not p.is_file():
        return None
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:
        return ["__SYNTAX_ERROR__"]
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append(node.module)
    return out


def _audit_py(rel: str) -> list[tuple[str, str, str]]:
    name = Path(rel).name
    imps = _imports(rel)
    if imps is None:
        return [(f"{name}_present", "fail", "missing"),
                (f"{name}_parses", "fail", "missing"),
                (f"{name}_no_llm_sdk", "fail", "missing"),
                (f"{name}_no_nondet", "fail", "missing")]
    if "__SYNTAX_ERROR__" in imps:
        return [(f"{name}_present", "pass", "exists"),
                (f"{name}_parses", "fail", "syntax_error"),
                (f"{name}_no_llm_sdk", "fail", "unparseable"),
                (f"{name}_no_nondet", "fail", "unparseable")]
    llm_hit = next((n for n in imps for b in _LLM_DENY if n == b or n.startswith(b + ".")), None)
    nondet_hit = next((n for n in imps for b in _NONDET_DENY if n == b or n.startswith(b + ".")), None)
    return [
        (f"{name}_present", "pass", "exists"),
        (f"{name}_parses", "pass", "parses"),
        (f"{name}_no_llm_sdk", "fail" if llm_hit else "pass", f"banned:{llm_hit}" if llm_hit else "clean"),
        (f"{name}_no_nondet", "fail" if nondet_hit else "pass", f"banned:{nondet_hit}" if nondet_hit else "clean"),
    ]


def collect(source_state: str) -> list[dict]:
    cp = _cp()
    md_present = (REPO_ROOT / f"{SKILL_REL}/SKILL.md").is_file()
    checks: list[tuple[str, str, str]] = [
        ("skill_md_present", "pass" if md_present else "fail", "exists" if md_present else "missing"),
    ]
    for fn in PY_FILES:
        checks.extend(_audit_py(f"{SKILL_REL}/{fn}"))
    return [_make({"check_id": cid, "verdict": v, "reason": r}, source_state, cp)
            for cid, v, r in checks]


def verify(data_point: dict) -> tuple[str, str]:
    return ("live", data_point["value"]["check_id"])
