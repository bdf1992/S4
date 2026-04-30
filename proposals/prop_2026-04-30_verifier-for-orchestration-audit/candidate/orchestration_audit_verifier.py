"""Candidate verify.py for skills/orchestration_audit — a Foundation-2
collector skill that turns 0.3 self-report (orchestration-log.jsonl)
into 0.1 measurement. Walks the bundle's source files plus its
collector-produced dataset and emits one bundle_self_check data point
per structural check.

Closes skill_without_verifier:facde0e22db9ffb6. On promotion, this
file moves to skills/orchestration_audit/verify.py.

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
SKILL_REL = "skills/orchestration_audit"
PY_FILES = ("collectors/orchestration_activations.py", "lib/data_point.py")
DATASET_FILES = ("datasets/orchestration_activations.jsonl",
                 "datasets/orchestration_activations.source_state")

COLLECTOR_ID = "orchestration_audit_verifier"
KIND = "bundle_self_check"
VALUE_SCHEMA = {"type": "object", "required": ["check_id", "verdict", "reason"]}
INPUTS = ([f"{SKILL_REL}/SKILL.md"]
          + [f"{SKILL_REL}/{f}" for f in PY_FILES]
          + [f"{SKILL_REL}/{f}" for f in DATASET_FILES])

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
    name = rel.split("/")[-1]
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
    nd_hit = next((n for n in imps for b in _NONDET_DENY if n == b or n.startswith(b + ".")), None)
    return [(f"{name}_present", "pass", "exists"),
            (f"{name}_parses", "pass", "parses"),
            (f"{name}_no_llm_sdk", "fail" if llm_hit else "pass", f"banned:{llm_hit}" if llm_hit else "clean"),
            (f"{name}_no_nondet", "fail" if nd_hit else "pass", f"banned:{nd_hit}" if nd_hit else "clean")]


def _present(rel: str, cid: str) -> tuple[str, str, str]:
    ok = (REPO_ROOT / rel).is_file()
    return (cid, "pass" if ok else "fail", "exists" if ok else "missing")


def collect(source_state: str) -> list[dict]:
    cp = _cp()
    checks: list[tuple[str, str, str]] = [_present(f"{SKILL_REL}/SKILL.md", "skill_md_present")]
    for fn in PY_FILES:
        checks.extend(_audit_py(f"{SKILL_REL}/{fn}"))
    for fn in DATASET_FILES:
        checks.append(_present(f"{SKILL_REL}/{fn}",
                               fn.split("/")[-1].replace(".", "_") + "_present"))
    return [_make({"check_id": cid, "verdict": v, "reason": r}, source_state, cp)
            for cid, v, r in checks]


def verify(data_point: dict) -> tuple[str, str]:
    return ("live", data_point["value"]["check_id"])
