"""verify.py — bundle walker for skills/subprotocol-for-claude-code, the
prior-art skill this experiment rides under. Heterogeneous bundle:
SKILL.md, overlay.md, references/ (yaml + markdown), scripts/
(two Python utilities). Walks named files and emits one
bundle_self_check data point per check.

Promoted from prop:2026-04-30:verifier-for-subprotocol-for-claude-code,
closing skill_without_verifier:b404f1c17d6e7d9d.

Foundation-2 conformant: deterministic, no LLM, declared inputs.

Usage:
  python -m skills.subprotocol-for-claude-code.verify
"""
from __future__ import annotations

import ast
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skills.leash_for_hooks.collectors import llm_sdk_denylist  # noqa: E402

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

_NONDET_DENY = ("random", "uuid", "secrets")


def _llm_deny() -> tuple[str, ...]:
    ss = llm_sdk_denylist.compute_source_state()
    return tuple(d["value"]["sdk_name"] for d in llm_sdk_denylist.collect(ss))


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


def _audit_py(rel: str, llm_deny: tuple[str, ...]) -> list[tuple[str, str, str]]:
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
    llm = next((n for n in imps for b in llm_deny if n == b or n.startswith(b + ".")), None)
    nd = next((n for n in imps for b in _NONDET_DENY if n == b or n.startswith(b + ".")), None)
    return [
        (f"{name}_parses", "pass", "parses"),
        (f"{name}_no_llm_sdk", "fail" if llm else "pass", f"banned:{llm}" if llm else "clean"),
        (f"{name}_no_nondet", "fail" if nd else "pass", f"banned:{nd}" if nd else "clean"),
    ]


def compute_source_state() -> str:
    h = hashlib.sha256()
    for fn in NAMED_FILES:
        p = REPO_ROOT / SKILL_REL / fn
        h.update(fn.encode()); h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest() if p.is_file() else b"\0" * 32)
    return "sha256:" + h.hexdigest()[:32]


def collect(source_state: str) -> list[dict]:
    cp = _cp()
    checks: list[tuple[str, str, str]] = []
    for fn in NAMED_FILES:
        present = (REPO_ROOT / f"{SKILL_REL}/{fn}").is_file()
        cid = fn.replace("/", "_").replace(".", "_") + "_present"
        checks.append((cid, "pass" if present else "fail", "exists" if present else "missing"))
    llm_deny = _llm_deny()
    for fn in PY_FILES:
        checks.extend(_audit_py(f"{SKILL_REL}/{fn}", llm_deny))
    return [_make({"check_id": cid, "verdict": v, "reason": r}, source_state, cp)
            for cid, v, r in checks]


def verify(data_point: dict) -> tuple[str, str]:
    if data_point["value"]["verdict"] == "pass":
        return ("live", data_point["value"]["check_id"])
    return ("dangling", f"self_check_fail:{data_point['value']['reason']}")


def main() -> int:
    ss = compute_source_state()
    rows = collect(ss)
    failures = [r for r in rows if r["value"]["verdict"] == "fail"]
    print(f"verify: {len(rows)} self-checks, {len(failures)} failures")
    for f in failures:
        print(f"  FAIL {f['value']['check_id']}: {f['value']['reason']}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
