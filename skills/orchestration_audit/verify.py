"""Bundle self-check for skills/orchestration_audit.

Walks the bundle's source + collector outputs + signal probes, runs
structural checks, and exits 0 iff every check passes. Emits one
bundle_self_check data point per check. Foundation 2 conformant:
deterministic, no LLM, declared inputs.

Checks:
- Required source files present and parseable
- No LLM SDK or nondeterminism imports in any collector / signal
- Every collector's verify(dp) returns 'live' on its own dataset
- Probe set runs and matches expected envelopes
- pfsm_parameters dataset reflects current activations corpus
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

from skills.orchestration_audit.lib import data_point as dp
from skills.orchestration_audit.collectors import (
    orchestration_activations as oa,
    decision_point_honesty as dph,
    pfsm_parameters as pp,
)
from skills.orchestration_audit.signals import trace_conformity as tc

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "orchestration_audit"

COLLECTOR_ID = "orchestration_audit_verify"
KIND = "bundle_self_check"

REQUIRED_PY = (
    "collectors/orchestration_activations.py",
    "collectors/decision_point_honesty.py",
    "collectors/pfsm_parameters.py",
    "signals/trace_conformity.py",
    "lib/data_point.py",
)
REQUIRED_DATA = (
    "datasets/orchestration_activations.jsonl",
    "datasets/decision_point_honesty.jsonl",
    "datasets/pfsm_parameters.jsonl",
    "probes/trace_conformity_probes.json",
)
LLM_DENY = ("anthropic", "openai", "google.generativeai", "cohere")
NONDET_DENY = ("random", "uuid", "secrets")


def _cp() -> dict:
    return {
        "kind": "collector", "target": {"collector_id": COLLECTOR_ID},
        "resolver": "collector_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved", "last_payload": None, "last_reason": None,
    }


def _check(check_id: str, ok: bool, reason: str) -> tuple[str, str, str]:
    return (check_id, "pass" if ok else "fail", reason)


def _audit_py(rel: str) -> list[tuple[str, str, str]]:
    p = SKILL / rel
    if not p.is_file():
        return [_check(f"{rel}_present", False, "missing")]
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return [_check(f"{rel}_present", True, "exists"),
                _check(f"{rel}_parses", False, f"syntax_error:{e.lineno}")]
    imps: list[str] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imps.extend(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            imps.append(n.module)
    llm_hit = next((m for m in imps for b in LLM_DENY if m == b or m.startswith(b + ".")), None)
    nd_hit = next((m for m in imps for b in NONDET_DENY if m == b or m.startswith(b + ".")), None)
    return [
        _check(f"{rel}_present", True, "exists"),
        _check(f"{rel}_parses", True, "parses"),
        _check(f"{rel}_no_llm_sdk", llm_hit is None, f"banned:{llm_hit}" if llm_hit else "clean"),
        _check(f"{rel}_no_nondet", nd_hit is None, f"banned:{nd_hit}" if nd_hit else "clean"),
    ]


def _check_collector_verify(name: str, mod) -> tuple[str, str, str]:
    path = SKILL / "datasets" / f"{mod.COLLECTOR_ID}.jsonl"
    if not path.is_file():
        return _check(f"{name}_dataset_present", False, "missing")
    dps = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not dps:
        return _check(f"{name}_dataset_nonempty", False, "empty")
    bad = [(d["id"], mod.verify(d)) for d in dps]
    dangling = [(i, r) for i, (s, r) in bad if s != "live"]
    if dangling:
        return _check(f"{name}_all_live", False, f"dangling:{len(dangling)}")
    return _check(f"{name}_all_live", True, f"{len(dps)}/{len(dps)}_live")


def _check_probes() -> list[tuple[str, str, str]]:
    pf = SKILL / "probes" / "trace_conformity_probes.json"
    if not pf.is_file():
        return [_check("probes_present", False, "missing")]
    out: list[tuple[str, str, str]] = [_check("probes_present", True, "exists")]
    spec = json.loads(pf.read_text(encoding="utf-8"))
    for p in spec["probes"]:
        r = tc.evaluate(p["trace"])
        e = p["expected"]
        reasons: list[str] = []
        if "verdict_in" in e and r["verdict"] not in e["verdict_in"]:
            reasons.append(f"verdict={r['verdict']}")
        if "verdict_not_in" in e and r["verdict"] in e["verdict_not_in"]:
            reasons.append(f"verdict_forbidden={r['verdict']}")
        if "top_class" in e and r.get("top_class") != e["top_class"]:
            reasons.append(f"top={r.get('top_class')}")
        if "confidence_min" in e and r["confidence"] < e["confidence_min"]:
            reasons.append(f"conf<{e['confidence_min']}")
        if "confidence_max" in e and r["confidence"] > e["confidence_max"]:
            reasons.append(f"conf>{e['confidence_max']}")
        if "gap_record_must_contain" in e:
            gr = r.get("gap_record", {})
            for k in e["gap_record_must_contain"]:
                if k not in gr:
                    reasons.append(f"gap_missing:{k}")
        out.append(_check(f"probe:{p['probe_id']}", not reasons, "ok" if not reasons else ";".join(reasons)))
    return out


def _check_pfsm_freshness() -> tuple[str, str, str]:
    """Verify pfsm_parameters was fit on the current activations corpus."""
    params_path = SKILL / "datasets" / "pfsm_parameters.jsonl"
    if not params_path.is_file():
        return _check("pfsm_freshness", False, "params_missing")
    line = next((l for l in params_path.read_text(encoding="utf-8").splitlines() if l.strip()), None)
    if not line:
        return _check("pfsm_freshness", False, "params_empty")
    rec = json.loads(line)
    expected_ss = pp.compute_source_state()
    actual_ss = rec["provenance"]["source_state"]
    return _check("pfsm_freshness",
                  actual_ss == expected_ss,
                  "fresh" if actual_ss == expected_ss else f"stale:{actual_ss[:18]}_vs_{expected_ss[:18]}")


def collect(source_state: str) -> list[dict]:
    cp = _cp()
    checks: list[tuple[str, str, str]] = []
    checks.append(_check("skill_md_present", (SKILL / "SKILL.md").is_file(), "exists"))
    checks.append(_check("design_doc_present", (SKILL / "0_2_design.md").is_file(), "exists"))
    for rel in REQUIRED_PY:
        checks.extend(_audit_py(rel))
    for rel in REQUIRED_DATA:
        checks.append(_check(f"{rel.split('/')[-1]}_present",
                             (SKILL / rel).is_file(),
                             "exists" if (SKILL / rel).is_file() else "missing"))
    checks.append(_check_collector_verify("activations", oa))
    checks.append(_check_collector_verify("honesty", dph))
    checks.append(_check_collector_verify("pfsm", pp))
    checks.append(_check_pfsm_freshness())
    checks.extend(_check_probes())
    return [dp.make_data_point(
        collector_id=COLLECTOR_ID, kind=KIND,
        value={"check_id": cid, "verdict": v, "reason": r},
        source_state=source_state, collector_pointer=cp,
    ) for cid, v, r in checks]


def verify(data_point: dict) -> tuple[str, str]:
    return ("live", data_point["value"]["check_id"])


def compute_source_state() -> str:
    import hashlib
    h = hashlib.sha256()
    for rel in REQUIRED_PY:
        p = SKILL / rel
        if p.is_file():
            h.update(rel.encode()); h.update(b"\0")
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32]


if __name__ == "__main__":
    ss = compute_source_state()
    dps = collect(ss)
    failed = [(d["value"]["check_id"], d["value"]["reason"])
              for d in dps if d["value"]["verdict"] != "pass"]
    print(f"orchestration_audit/verify.py — {len(dps)} checks, "
          f"{len(dps) - len(failed)} pass, {len(failed)} fail")
    for cid, reason in failed:
        print(f"  FAIL {cid}: {reason}", file=sys.stderr)
    if failed:
        sys.exit(1)
    print("all checks pass")
    sys.exit(0)
