"""verify.py — the 0.4 grading walker for the regime_audit bundle.

Runs the grading procedure declared in foundations/zero-four.md against
the skill itself (always) and optionally against a specific output bundle
(when given as argv[1]).

Structurally a 0.1 collector that emits bundle_self_check data points,
one per checked component. main() prints a summary and exits 0 if every
emitted self-check passed.

Usage:
  python -m skills.regime_audit.verify
  python -m skills.regime_audit.verify outputs/run-XXX
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from skills.leash_for_hooks.collectors import llm_sdk_denylist
from skills.regime_audit.collectors import regime_classification
from skills.regime_audit.lib import audit, collection_program as cp, data_point as dp
from skills.regime_audit.signals import regime_distribution

COLLECTOR_ID = "verify"
KIND = "bundle_self_check"
VALUE_SCHEMA = {"type": "object", "required": ["component", "role", "status"]}
INPUTS = [
    "skills/regime_audit/collectors/*.py",
    "skills/regime_audit/signals/*.py",
    "skills/regime_audit/lib/*.py",
    "skills/regime_audit/orchestrate.py",
    "skills/regime_audit/outputs/*",
]

SKILL = Path(__file__).resolve().parent
COLLECTORS = (regime_classification,)
SIGNALS = (regime_distribution,)


def _check(component: str, role: str, status: str, **extra) -> dict:
    return {"component": component, "role": role, "status": status, **extra}


def _collector_pointer() -> dict:
    return {"kind": "collector", "target": {"collector_id": COLLECTOR_ID},
            "resolver": "collector_resolver",
            "bound_at": {"source_state": None, "resolved_at": None},
            "last_status": "unresolved", "last_payload": None, "last_reason": None}


def compute_source_state() -> str:
    h = hashlib.sha256()
    for sub in ("collectors", "signals", "lib"):
        for p in sorted((SKILL / sub).glob("*.py")):
            h.update(p.name.encode()); h.update(b"\0")
            h.update(hashlib.sha256(p.read_bytes()).digest())
    h.update((SKILL / "orchestrate.py").read_bytes())
    return "sha256:" + h.hexdigest()[:32]


def _denylist_set() -> frozenset[str]:
    ss = llm_sdk_denylist.compute_source_state()
    return frozenset(d["value"]["sdk_name"] for d in llm_sdk_denylist.collect(ss))


def _check_collectors(denylist: frozenset[str]) -> list[dict]:
    out = []
    for mod in COLLECTORS:
        path = Path(mod.__file__)
        ok, vios = cp.validate_collector(path, llm_sdk_denylist=denylist)
        out.append(_check(mod.COLLECTOR_ID, "collector",
                          "pass" if ok else "fail", violations=vios))
        ss = mod.compute_source_state()
        rows1 = mod.collect(ss); rows2 = mod.collect(ss)
        same = ([{**r, "provenance": {**r["provenance"], "collected_at": "X"}} for r in rows1]
                == [{**r, "provenance": {**r["provenance"], "collected_at": "X"}} for r in rows2])
        out.append(_check(mod.COLLECTOR_ID, "determinism",
                          "pass" if same else "fail"))
    return out


def _check_signals() -> list[dict]:
    out = []
    for mod in SIGNALS:
        probes = mod.run_probes()
        all_pass = all(p["pass"] for p in probes)
        out.append(_check(mod.SIGNAL_ID, "signal",
                          "pass" if all_pass else "fail", probes=probes))
    return out


def _check_data_points() -> list[dict]:
    out = []
    for mod in COLLECTORS:
        ds = SKILL / "datasets" / f"{mod.COLLECTOR_ID}.jsonl"
        rows = dp.read_jsonl(ds)
        bad = []
        for r in rows:
            ok, reason = dp.validate(r)
            if not ok:
                bad.append({"id": r.get("id", "?"), "reason": reason})
        out.append(_check(mod.COLLECTOR_ID, "dataset_schema",
                          "pass" if not bad else "fail",
                          row_count=len(rows), bad=bad[:5]))
    return out


def _check_orchestration_decision_points() -> list[dict]:
    src = (SKILL / "orchestrate.py").read_text(encoding="utf-8")
    declared = ["dataset_present", "distribution_fit"]
    fences = ["regime_classification", "regime_distribution"]
    missing = [d for d in declared if f'"{d}"' not in src]
    missing_fences = [f for f in fences if f not in src]
    ok, vios = audit.audit_program(SKILL / "orchestrate.py",
                                   llm_sdk_denylist=_denylist_set(),
                                   budget=audit.DEFAULT_ORCHESTRATION_BUDGET)
    return [_check("orchestrate.py", "orchestration",
                   "pass" if not (missing or missing_fences) and ok else "fail",
                   missing_decisions=missing, missing_fences=missing_fences,
                   audit_violations=vios)]


def _check_output_bundle(bundle_dir: Path) -> list[dict]:
    out = []
    mp = bundle_dir / "manifest.json"
    if not mp.exists():
        return [_check(str(bundle_dir.name), "output_bundle", "fail",
                       reason="manifest_missing")]
    manifest = json.loads(mp.read_text(encoding="utf-8"))
    log = dp.read_jsonl(bundle_dir / "orchestration-log.jsonl")
    decided = [e["decision_id"] for e in log]
    expected = [d[0] for d in manifest.get("decision_points", [])]
    decisions_ok = decided == expected[:len(decided)]
    out.append(_check(bundle_dir.name, "output_bundle.decisions_in_order",
                      "pass" if decisions_ok else "fail",
                      observed=decided, expected=expected))
    claim = manifest.get("claim")
    out.append(_check(bundle_dir.name, "output_bundle.claim_consistency",
                      "pass" if claim in ("aggregated", "no_data") else "fail",
                      claim=claim))
    return out


def collect(source_state: str) -> list[dict]:
    denylist = _denylist_set()
    rows: list[dict] = []
    rows += _check_collectors(denylist)
    rows += _check_signals()
    rows += _check_data_points()
    rows += _check_orchestration_decision_points()
    if len(sys.argv) > 1:
        bundle = Path(sys.argv[1])
        if not bundle.is_absolute():
            bundle = SKILL.parents[1] / bundle
        rows += _check_output_bundle(bundle)
    cp_ptr = _collector_pointer()
    return [dp.make_data_point(collector_id=COLLECTOR_ID, kind=KIND, value=r,
                               source_state=source_state, collector_pointer=cp_ptr)
            for r in rows]


def verify(data_point: dict) -> tuple[str, str]:
    return ("live", "self_check") if data_point["value"]["status"] == "pass" else ("dangling", "self_check_fail")


def main() -> int:
    ss = compute_source_state()
    rows = collect(ss)
    failures = [r for r in rows if r["value"]["status"] == "fail"]
    print(f"verify: {len(rows)} self-checks, {len(failures)} failures")
    for f in failures:
        print(f"  FAIL [{f['value']['role']}] {f['value']['component']}: "
              f"{ {k:v for k,v in f['value'].items() if k not in ('status','role','component')} }")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
