"""Candidate verify.py for skills/regime_audit_report — a pure-render
skill (stats.json -> report.md) with no collectors or orchestration.
Walks the skill's source files and emits one bundle_self_check data
point per structural check.

Closes skill_without_verifier:756c48fe81d375a5. On promotion, this
file moves to skills/regime_audit_report/verify.py.

Foundation-2 conformant: deterministic, no LLM, declared inputs,
audit budget under 80 lines. Helpers inlined so the candidate is
self-contained and promotion does not require re-pathing imports.
"""
from __future__ import annotations

import ast
import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_REL = "skills/regime_audit_report"

COLLECTOR_ID = "regime_audit_report_verifier"
KIND = "bundle_self_check"
VALUE_SCHEMA = {"type": "object", "required": ["check_id", "verdict", "reason"]}
INPUTS = [f"{SKILL_REL}/SKILL.md", f"{SKILL_REL}/render.py", f"{SKILL_REL}/__init__.py"]

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


def _imports(rel: str) -> list[str]:
    p = REPO_ROOT / rel
    if not p.is_file():
        return []
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


def _check_imports(rel: str, deny: tuple[str, ...]) -> tuple[str, str]:
    imps = _imports(rel)
    if not imps:
        return "fail", "missing_or_empty"
    if "__SYNTAX_ERROR__" in imps:
        return "fail", "unparseable"
    for n in imps:
        for bad in deny:
            if n == bad or n.startswith(bad + "."):
                return "fail", f"banned_import:{n}"
    return "pass", "clean"


def collect(source_state: str) -> list[dict]:
    cp = _cp()
    md = (REPO_ROOT / f"{SKILL_REL}/SKILL.md").is_file()
    rp = REPO_ROOT / f"{SKILL_REL}/render.py"
    rp_exists = rp.is_file()
    rp_parses = "fail"
    rp_parse_reason = "missing"
    if rp_exists:
        try:
            ast.parse(rp.read_text(encoding="utf-8"))
            rp_parses, rp_parse_reason = "pass", "parses"
        except SyntaxError as e:
            rp_parse_reason = f"syntax_error:{e.lineno}"
    checks = [
        ("skill_md_present", "pass" if md else "fail", "exists" if md else "missing"),
        ("render_py_present", "pass" if rp_exists else "fail", "exists" if rp_exists else "missing"),
        ("render_py_parses", rp_parses, rp_parse_reason),
        ("render_py_no_llm_sdk", *_check_imports(f"{SKILL_REL}/render.py", _LLM_DENY)),
        ("render_py_no_nondet", *_check_imports(f"{SKILL_REL}/render.py", _NONDET_DENY)),
    ]
    return [_make({"check_id": cid, "verdict": v, "reason": r}, source_state, cp)
            for cid, v, r in checks]


def verify(data_point: dict) -> tuple[str, str]:
    cid = data_point["value"]["check_id"]
    expected = {"skill_md_present", "render_py_present", "render_py_parses",
                "render_py_no_llm_sdk", "render_py_no_nondet"}
    return ("live", cid) if cid in expected else ("dangling", "unknown_check_id")
