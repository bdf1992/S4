"""0.3 orchestration entry point for the leash-for-slash-commands skill.

Runs all collectors, persists their outputs to datasets/, fits the two
signals on those datasets, evaluates a candidate slash command through
the declared decision points, and emits a bundle directory.

Decision points are declared at module top so verify.py can structurally
check that the source consults exactly these fences in this order.

Usage:
  python -m skills.leash_for_slash_commands.orchestrate
  python -m skills.leash_for_slash_commands.orchestrate cand.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from skills.leash_for_hooks.lib import data_point as dp, leash_state as ls
from skills.leash_for_hooks.signals import emission_readiness

from .collectors import (slash_command_decl, slash_command_config,
                         exemplar_bundle_state)
from .signals import slash_command_collision

DECISION_POINTS = [
    ("name_validity", "slash_command_decl"),         # 0.1 dataset NON-membership
    ("collision_check", "slash_command_collision"),  # 0.2 signal
    ("emission_gate", "emission_readiness"),         # 0.2 shared signal
]

COLLECTORS = (slash_command_decl, slash_command_config, exemplar_bundle_state)
SKILL_ROOT = Path(__file__).resolve().parent
DATASETS = SKILL_ROOT / "datasets"
OUTPUTS = SKILL_ROOT / "outputs"

DEFAULT_CANDIDATE = {"name": "deploy-staging", "scope": "user"}


def run_all_collectors() -> dict:
    out: dict[str, dict] = {}
    for mod in COLLECTORS:
        ss = mod.compute_source_state()
        rows = mod.collect(ss)
        path = DATASETS / f"{mod.COLLECTOR_ID}.jsonl"
        dp.write_jsonl(path, rows)
        (DATASETS / f"{mod.COLLECTOR_ID}.source_state").write_text(ss, encoding="utf-8")
        out[mod.COLLECTOR_ID] = {"source_state": ss, "row_count": len(rows),
                                 "dataset_path": str(path.relative_to(SKILL_ROOT))}
    return out


def _decision(decision_id: str, fence_id: str, *, input_payload, result, branch: str) -> dict:
    return {"decision_id": decision_id, "fence_id": fence_id,
            "input_payload": input_payload, "result": result, "branch_taken": branch}


def evaluate_candidate(candidate: dict) -> tuple[list[dict], dict]:
    log: list[dict] = []
    state = ls.read(SKILL_ROOT)
    leashed, reason = ls.is_leashed(state, candidate, key="name")
    log.append(_decision("toggle_check", "leash_state",
                         input_payload={"name": candidate.get("name")},
                         result={"leashed": leashed, "reason": reason, "state": state},
                         branch="leashed" if leashed else "unleashed"))
    if not leashed:
        return log, {"verdict": "unleashed", "reason": reason,
                     "candidate_command": candidate, "leash_state": state}
    # Decision 1: name_validity (0.1 dataset NON-membership against reserved)
    reserved = {r["value"]["name"] for r in dp.read_jsonl(DATASETS / "slash_command_decl.jsonl")}
    cand_name = candidate.get("name", "").lower()
    branch1 = "reserved" if cand_name in reserved else "valid"
    log.append(_decision("name_validity", "slash_command_decl",
                         input_payload={"name": cand_name},
                         result={"verdict": branch1, "reserved_names": sorted(reserved)},
                         branch=branch1))
    if branch1 == "reserved":
        return log, {"verdict": "rejected", "reason": "shadows_reserved_name"}
    # Decision 2: slash_command_collision (0.2 signal)
    sc_rows = dp.read_jsonl(DATASETS / "slash_command_config.jsonl")
    fitted = slash_command_collision.fit(sc_rows)
    coll_result = slash_command_collision.evaluate(
        candidate, fitted_hashes=fitted, training_rows=sc_rows)
    log.append(_decision("collision_check", "slash_command_collision",
                         input_payload=candidate, result=coll_result,
                         branch=coll_result["verdict"]))
    if coll_result["verdict"] == "collides":
        return log, {"verdict": "rejected", "reason": "collides_with_existing_command"}
    # Decision 3: emission_readiness (0.2 shared signal)
    ex_rows = dp.read_jsonl(DATASETS / "exemplar_bundle_state.jsonl")
    bundle_state = {
        "dataset_sizes": {mod.COLLECTOR_ID: len(dp.read_jsonl(DATASETS / f"{mod.COLLECTOR_ID}.jsonl"))
                          for mod in COLLECTORS},
        "all_collectors_passed": True,
    }
    er_fitted = emission_readiness.fit(ex_rows)
    er_result = emission_readiness.evaluate(bundle_state,
                                            fitted=er_fitted, training_rows=ex_rows)
    log.append(_decision("emission_gate", "emission_readiness",
                         input_payload=bundle_state, result=er_result,
                         branch=er_result["verdict"]))
    return log, {
        "verdict": "0.4" if er_result["verdict"] == "ready" else "candidate",
        "candidate_command": candidate,
        "bundle_state": bundle_state,
        "emission_signal": er_result,
    }


def emit_bundle(collector_summary: dict, log: list[dict], outcome: dict) -> Path:
    run_id = "run-" + dp.content_hash({"log": log, "outcome": outcome})
    bdir = OUTPUTS / run_id
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / "candidate.json").write_text(json.dumps(outcome, indent=2, sort_keys=True), encoding="utf-8")
    dp.write_jsonl(bdir / "orchestration-log.jsonl", log)
    manifest = {
        "claim": outcome["verdict"],  # "0.4" | "candidate" | "rejected" | "unleashed"
        "collectors": collector_summary,
        "decision_points": [list(x) for x in DECISION_POINTS],
        "leash_state": ls.read(SKILL_ROOT),
        "log_path": "orchestration-log.jsonl",
        "candidate_path": "candidate.json",
        "skill_root": str(SKILL_ROOT.relative_to(SKILL_ROOT.parents[1])),
    }
    if outcome.get("verdict") == "candidate":
        proposed = SKILL_ROOT / "exemplars" / "proposed"
        proposed.mkdir(parents=True, exist_ok=True)
        bundle_state_record = {"bundle_id": run_id, **outcome["bundle_state"]}
        (proposed / f"{run_id}.json").write_text(
            json.dumps(bundle_state_record, indent=2, sort_keys=True), encoding="utf-8")
        manifest["proposed_exemplar"] = f"exemplars/proposed/{run_id}.json"
    (bdir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return bdir


def main() -> int:
    candidate = DEFAULT_CANDIDATE
    if len(sys.argv) > 1:
        candidate = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    summary = run_all_collectors()
    log, outcome = evaluate_candidate(candidate)
    bdir = emit_bundle(summary, log, outcome)
    print(f"emitted bundle: {bdir.relative_to(SKILL_ROOT.parents[1])}  claim={outcome['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
