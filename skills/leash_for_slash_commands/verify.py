"""verify.py — the 0.4 grading walker for the leash-for-slash-commands bundle.

Sibling of skills/leash_for_hooks/verify.py — same shape, different
COLLECTORS/SIGNALS/decision points. Imports the bedrock validators and
shared resolvers/signals from leash_for_hooks (round-2 reuse: copy
deferred until a third sibling exists, per recursion-seam.md step 4).

Usage:
  python -m skills.leash_for_slash_commands.verify
  python -m skills.leash_for_slash_commands.verify outputs/run-XXX
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from skills.leash_for_hooks.collectors import llm_sdk_denylist
from skills.leash_for_hooks.lib import (audit, collection_program as cp,
                                        data_point as dp, leash_state as ls)
from skills.leash_for_hooks.resolvers import collector as collector_resolver
from skills.leash_for_hooks.resolvers import data_point as data_point_resolver
from skills.leash_for_hooks.resolvers import file_line as file_line_resolver
from skills.leash_for_hooks.signals import emission_readiness

from skills.leash_for_slash_commands.collectors import (slash_command_decl, slash_command_config,
                                                        exemplar_bundle_state)
from skills.leash_for_slash_commands.signals import slash_command_collision

COLLECTOR_ID = "verify"
KIND = "bundle_self_check"
VALUE_SCHEMA = {"type": "object", "required": ["component", "role", "status"]}
INPUTS = [
    "skills/leash_for_slash_commands/collectors/*.py",
    "skills/leash_for_slash_commands/signals/*.py",
    "skills/leash_for_slash_commands/orchestrate.py",
    "skills/leash_for_slash_commands/outputs/*",
]

SKILL = Path(__file__).resolve().parent
REPO_ROOT = SKILL.parents[1]
COLLECTORS = (slash_command_decl, slash_command_config, exemplar_bundle_state)
SHARED_COLLECTORS = (llm_sdk_denylist,)
RESOLVERS = (file_line_resolver, collector_resolver, data_point_resolver)
SIGNALS = (slash_command_collision, emission_readiness)


def _check(component: str, role: str, status: str, **extra) -> dict:
    return {"component": component, "role": role, "status": status, **extra}


def _collector_pointer() -> dict:
    return {"kind": "collector", "target": {"collector_id": COLLECTOR_ID},
            "resolver": "collector_resolver",
            "bound_at": {"source_state": None, "resolved_at": None},
            "last_status": "unresolved", "last_payload": None, "last_reason": None}


def compute_source_state() -> str:
    h = hashlib.sha256()
    for sub in ("collectors", "signals"):
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
    for mod in COLLECTORS + SHARED_COLLECTORS:
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


def _check_resolvers(denylist: frozenset[str]) -> list[dict]:
    out = []
    for mod in RESOLVERS:
        path = Path(mod.__file__)
        ok, vios = cp.validate_resolver(path, llm_sdk_denylist=denylist)
        out.append(_check(mod.RESOLVER_ID, "resolver",
                          "pass" if ok else "fail", violations=vios))
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
            if not ok: bad.append({"id": r.get("id", "?"), "reason": reason})
        out.append(_check(mod.COLLECTOR_ID, "dataset_schema",
                          "pass" if not bad else "fail",
                          row_count=len(rows), bad=bad[:5]))
    return out


def _check_orchestration_decision_points() -> list[dict]:
    src = (SKILL / "orchestrate.py").read_text(encoding="utf-8")
    declared = ["name_validity", "collision_check", "emission_gate"]
    fences = ["slash_command_decl", "slash_command_collision", "emission_readiness"]
    missing = [d for d in declared if f'"{d}"' not in src]
    missing_fences = [f for f in fences if f not in src]
    toggle_wired = ("leash_state" in src and "is_leashed" in src
                    and "toggle_check" in src)
    ok, vios = audit.audit_program(SKILL / "orchestrate.py",
                                   llm_sdk_denylist=_denylist_set(),
                                   budget=audit.DEFAULT_ORCHESTRATION_BUDGET)
    return [_check("orchestrate.py", "orchestration",
                   "pass" if not (missing or missing_fences) and ok and toggle_wired else "fail",
                   missing_decisions=missing, missing_fences=missing_fences,
                   toggle_wired=toggle_wired, audit_violations=vios)]


def _check_leash_state() -> list[dict]:
    path = SKILL / ls.FILENAME
    if not path.exists():
        return [_check(ls.FILENAME, "leash_state", "fail", reason="file_missing")]
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [_check(ls.FILENAME, "leash_state", "fail", reason=f"json_decode:{exc}")]
    ok, reason = ls.validate(state)
    return [_check(ls.FILENAME, "leash_state",
                   "pass" if ok else "fail",
                   state=state, validation_reason=reason or "ok")]


def _check_validation_receipts(manifest: dict) -> dict:
    receipts = manifest.get("validation_receipts", {})
    missing = []
    walker = receipts.get("bundle_walker")
    if not walker or not (SKILL / walker).exists():
        missing.append("bundle_walker")
    for cid, meta in receipts.get("collector_receipts", {}).items():
        for key in ("dataset", "source_state"):
            rel = meta.get(key)
            if not rel or not (SKILL / rel).exists():
                missing.append(f"collector_receipts.{cid}.{key}")
    for sid, rel in receipts.get("signal_probe_runners", {}).items():
        if not rel or not (REPO_ROOT / rel).exists():
            missing.append(f"signal_probe_runners.{sid}")
    expected_collectors = {mod.COLLECTOR_ID for mod in COLLECTORS}
    expected_signals = {mod.SIGNAL_ID for mod in SIGNALS}
    declared_collectors = set(receipts.get("collector_receipts", {}))
    declared_signals = set(receipts.get("signal_probe_runners", {}))
    missing.extend(f"collector_receipts.{cid}" for cid in sorted(expected_collectors - declared_collectors))
    missing.extend(f"signal_probe_runners.{sid}" for sid in sorted(expected_signals - declared_signals))
    return _check("validation_receipts", "output_bundle.validation_receipts",
                  "pass" if not missing else "fail", missing=missing)


def _check_output_bundle(bundle_dir: Path) -> list[dict]:
    out = []
    mp = bundle_dir / "manifest.json"
    if not mp.exists():
        return [_check(str(bundle_dir.name), "output_bundle", "fail",
                       reason="manifest_missing")]
    manifest = json.loads(mp.read_text(encoding="utf-8"))
    log = dp.read_jsonl(bundle_dir / "orchestration-log.jsonl")
    decided = [e["decision_id"] for e in log]
    claim = manifest.get("claim")
    toggle_first = bool(decided) and decided[0] == "toggle_check"
    surface_decided = decided[1:] if toggle_first else decided
    if claim == "unleashed":
        decisions_ok = toggle_first and surface_decided == []
    elif claim == "rejected":
        expected = [d[0] for d in manifest.get("decision_points", [])]
        decisions_ok = toggle_first and len(surface_decided) >= 1 and \
            surface_decided == expected[:len(surface_decided)]
    else:
        expected = [d[0] for d in manifest.get("decision_points", [])]
        decisions_ok = toggle_first and surface_decided == expected
    out.append(_check(bundle_dir.name, "output_bundle.decisions_in_order",
                      "pass" if decisions_ok else "fail",
                      claim=claim, observed=decided,
                      expected_surface=[d[0] for d in manifest.get("decision_points", [])],
                      toggle_first=toggle_first))
    out.append(_check(bundle_dir.name, "output_bundle.claim_consistency",
                      "pass" if claim in ("0.4", "candidate", "rejected", "unleashed") else "fail",
                      claim=claim))
    out.append(_check_validation_receipts(manifest))
    return out


def collect(source_state: str) -> list[dict]:
    denylist = _denylist_set()
    rows: list[dict] = []
    rows += _check_collectors(denylist)
    rows += _check_resolvers(denylist)
    rows += _check_signals()
    rows += _check_data_points()
    rows += _check_orchestration_decision_points()
    rows += _check_leash_state()
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
