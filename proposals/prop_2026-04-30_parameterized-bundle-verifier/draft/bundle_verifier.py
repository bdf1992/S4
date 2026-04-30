"""bundle_verifier — parameterized verify.py library.

Each per-skill verify.py declares a manifest (skill_rel, presence files,
python-audit files) and delegates collect/verify to this module. One
audit budget covers all skills; one denylist source covers all skills.

Production landing zone (after promotion): skills/bundle_verifier/bundle_verifier.py.
Per-skill verify.py shrinks to ~20-line shims that import this and
declare their manifest as module-level constants.

Foundation-2 conformant: deterministic, no LLM, declared inputs.
"""
from __future__ import annotations

import ast
import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any

def _find_repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p.parent != p:
        if (p / "foundations").is_dir() and (p / "skills").is_dir():
            return p
        p = p.parent
    raise RuntimeError("repo root not found")


REPO_ROOT = _find_repo_root()

KIND = "bundle_self_check"
VALUE_SCHEMA = {"type": "object", "required": ["check_id", "verdict", "reason"]}

_LLM_DENY = ("anthropic", "openai", "google.generativeai", "cohere")
_NONDET_DENY = ("random", "uuid", "secrets")


def compute_inputs(skill_rel: str, presence: list[str], python_audit: list[str]) -> list[str]:
    return [f"{skill_rel}/{f}" for f in (*presence, *python_audit)]


def _cid(rel: str, suffix: str) -> str:
    return rel.replace("/", "_").replace(".", "_") + "_" + suffix


def _cp(collector_id: str) -> dict:
    return {"kind": "collector", "target": {"collector_id": collector_id},
            "resolver": "collector_resolver",
            "bound_at": {"source_state": None, "resolved_at": None},
            "last_status": "unresolved", "last_payload": None, "last_reason": None}


def _make(collector_id: str, value: Any, source_state: str, cp: dict) -> dict:
    canon = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    h = hashlib.sha256(canon).hexdigest()[:16]
    iso = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    return {"id": f"{collector_id}:{h}", "kind": KIND, "value": value,
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
    imps = _imports(rel)
    if imps is None:
        return [(_cid(rel, s), "fail", "missing")
                for s in ("present", "parses", "no_llm_sdk", "no_nondet")]
    if "__SYNTAX_ERROR__" in imps:
        return [(_cid(rel, "present"), "pass", "exists"),
                (_cid(rel, "parses"), "fail", "syntax_error"),
                (_cid(rel, "no_llm_sdk"), "fail", "unparseable"),
                (_cid(rel, "no_nondet"), "fail", "unparseable")]
    llm = next((n for n in imps for b in _LLM_DENY if n == b or n.startswith(b + ".")), None)
    nd = next((n for n in imps for b in _NONDET_DENY if n == b or n.startswith(b + ".")), None)
    return [(_cid(rel, "present"), "pass", "exists"),
            (_cid(rel, "parses"), "pass", "parses"),
            (_cid(rel, "no_llm_sdk"), "fail" if llm else "pass", f"banned:{llm}" if llm else "clean"),
            (_cid(rel, "no_nondet"), "fail" if nd else "pass", f"banned:{nd}" if nd else "clean")]


def collect(collector_id: str, skill_rel: str, presence: list[str],
            python_audit: list[str], source_state: str) -> list[dict]:
    cp = _cp(collector_id)
    checks: list[tuple[str, str, str]] = []
    for fn in presence:
        rel = f"{skill_rel}/{fn}"
        ok = (REPO_ROOT / rel).is_file()
        checks.append((_cid(rel, "present"),
                       "pass" if ok else "fail",
                       "exists" if ok else "missing"))
    for fn in python_audit:
        checks.extend(_audit_py(f"{skill_rel}/{fn}"))
    return [_make(collector_id, {"check_id": cid, "verdict": v, "reason": r}, source_state, cp)
            for cid, v, r in checks]


def verify(data_point: dict) -> tuple[str, str]:
    return ("live", data_point["value"]["check_id"])
