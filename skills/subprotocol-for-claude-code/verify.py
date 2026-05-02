"""Candidate verify.py for skills/subprotocol-for-claude-code — the
prior-art skill this experiment rides under. Heterogeneous bundle:
SKILL.md, overlay.md, references/ (yaml + markdown), reports/, scripts/
(two Python utilities). Walks named files and emits one
bundle_self_check data point per check.

Closes skill_without_verifier:b404f1c17d6e7d9d. On promotion, this
file moves to skills/subprotocol-for-claude-code/verify.py.

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
SKILL_REL = "skills/subprotocol-for-claude-code"
NAMED_FILES = (
    "SKILL.md", "overlay.md",
    "references/domain-configuration-schema.md",
    "references/domain-configuration.yaml",
    "references/translation-map.md",
    "scripts/setup-interview.py", "scripts/sync.py",
)
PY_FILES = ("scripts/setup-interview.py", "scripts/sync.py")

COLLECTOR_ID = "subprotocol_for_claude_code_verifier"
KIND = "bundle_self_check"
VALUE_SCHEMA = {"type": "object", "required": ["check_id", "verdict", "reason"]}
INPUTS = [f"{SKILL_REL}/{f}" for f in NAMED_FILES]

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


def _audit_py(rel: str) -> list[tuple[str, str, str]]:
    name = Path(rel).name
    p = REPO_ROOT / rel
    if not p.is_file():
        return [(f"{name}_parses", "fail", "missing"),
                (f"{name}_no_llm_sdk", "fail", "missing"),
                (f"{name}_no_nondet", "fail", "missing")]
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return [(f"{name}_parses", "fail", f"syntax_error:{e.lineno}"),
                (f"{name}_no_llm_sdk", "fail", "unparseable"),
                (f"{name}_no_nondet", "fail", "unparseable")]
    imps: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imps.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imps.append(node.module)
    llm = next((n for n in imps for b in _LLM_DENY if n == b or n.startswith(b + ".")), None)
    nd = next((n for n in imps for b in _NONDET_DENY if n == b or n.startswith(b + ".")), None)
    return [
        (f"{name}_parses", "pass", "parses"),
        (f"{name}_no_llm_sdk", "fail" if llm else "pass", f"banned:{llm}" if llm else "clean"),
        (f"{name}_no_nondet", "fail" if nd else "pass", f"banned:{nd}" if nd else "clean"),
    ]


def collect(source_state: str) -> list[dict]:
    cp = _cp()
    checks: list[tuple[str, str, str]] = []
    for fn in NAMED_FILES:
        present = (REPO_ROOT / f"{SKILL_REL}/{fn}").is_file()
        cid = fn.replace("/", "_").replace(".", "_") + "_present"
        checks.append((cid, "pass" if present else "fail", "exists" if present else "missing"))
    for fn in PY_FILES:
        checks.extend(_audit_py(f"{SKILL_REL}/{fn}"))
    return [_make({"check_id": cid, "verdict": v, "reason": r}, source_state, cp)
            for cid, v, r in checks]


def verify(data_point: dict) -> tuple[str, str]:
    return ("live", data_point["value"]["check_id"])
