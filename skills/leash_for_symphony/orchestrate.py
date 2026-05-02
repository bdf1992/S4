"""0.3 orchestration entry point for the leash-for-symphony skill.

Runs all collectors, persists their outputs to datasets/, fits the two
signals on those datasets, evaluates a candidate Symphony WORKFLOW.md
(parsed front matter, JSON-shaped) through the declared decision points,
and emits a bundle directory.

The toggle gate consults leash_state.json and additionally honors the
orthogonal `vocal` boolean: when state=off and vocal=true, the bundle
still includes a vocal_capture_plan.md describing how the operator
should wire `hooks.after_run` in the candidate WORKFLOW.md to pipe
Symphony's per-run event stream back into outputs/<run-id>/.

Usage:
  python -m skills.leash_for_symphony.orchestrate
  python -m skills.leash_for_symphony.orchestrate cand.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from skills.leash_for_hooks.lib import data_point as dp, leash_state as ls
from skills.leash_for_hooks.lib.receipts import validation_receipts
from skills.leash_for_hooks.signals import emission_readiness

from .collectors import (symphony_field_decl, symphony_workflow,
                         exemplar_bundle_state)
from .signals import symphony_permission_posture

DECISION_POINTS = [
    ("workflow_field_validity", "symphony_field_decl"),          # 0.1 dataset membership
    ("permission_posture_check", "symphony_permission_posture"), # 0.2 signal
    ("emission_gate", "emission_readiness"),                     # 0.2 shared signal
]

COLLECTORS = (symphony_field_decl, symphony_workflow, exemplar_bundle_state)
SKILL_ROOT = Path(__file__).resolve().parent
DATASETS = SKILL_ROOT / "datasets"
OUTPUTS = SKILL_ROOT / "outputs"

DEFAULT_CANDIDATE = {
    "candidate_id": "default-low-risk", "tracker": {"kind": "github", "repo_owner": "example", "repo_name": "example"},
    "polling": {"interval_ms": 30000}, "workspace": {"root": "~/symphony_workspaces"},
    "agent": {"adapter": "claude", "max_concurrent_agents": 2}, "claude": {"skip_permissions": False, "permission_mode": "default"},
}


def _flatten_candidate_paths(d: dict, prefix: str = "") -> list[str]:
    out: list[str] = []
    for k, v in sorted(d.items()):
        if k == "candidate_id":
            continue
        path = f"{prefix}{k}".lower()
        if isinstance(v, dict):
            out.extend(_flatten_candidate_paths(v, path + "."))
        else:
            out.append(path)
    return out


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
    vocal = ls.is_vocal(state)
    leashed, reason = ls.is_leashed(state, candidate, key="candidate_id")
    log.append(_decision("toggle_check", "leash_state",
                         input_payload={"candidate_id": candidate.get("candidate_id")},
                         result={"leashed": leashed, "reason": reason,
                                 "state": state, "vocal": vocal},
                         branch="leashed" if leashed else "unleashed"))
    if not leashed:
        return log, {"verdict": "unleashed", "reason": reason,
                     "candidate_workflow": candidate, "leash_state": state,
                     "vocal": vocal}
    # Decision 1: workflow_field_validity (0.1 dataset membership)
    declared_paths = {r["value"]["field_path"]
                      for r in dp.read_jsonl(DATASETS / "symphony_field_decl.jsonl")}
    cand_paths = _flatten_candidate_paths(candidate)
    unknown = sorted(p for p in cand_paths if p not in declared_paths)
    branch1 = "unknown_fields" if unknown else "valid"
    log.append(_decision("workflow_field_validity", "symphony_field_decl",
                         input_payload={"field_paths": cand_paths},
                         result={"verdict": branch1, "unknown_fields": unknown,
                                 "declared_count": len(declared_paths)},
                         branch=branch1))
    if branch1 == "unknown_fields":
        return log, {"verdict": "rejected", "reason": "unknown_workflow_fields",
                     "unknown_fields": unknown, "vocal": vocal}
    # Decision 2: permission_posture (0.2 signal)
    sw_rows = dp.read_jsonl(DATASETS / "symphony_workflow.jsonl")
    fitted = symphony_permission_posture.fit(sw_rows)
    pp_result = symphony_permission_posture.evaluate(
        candidate, fitted_modes=fitted, training_rows=sw_rows)
    log.append(_decision("permission_posture_check", "symphony_permission_posture",
                         input_payload=candidate, result=pp_result,
                         branch=pp_result["verdict"]))
    if pp_result["verdict"] == "posture_drift":
        return log, {"verdict": "rejected", "reason": "permission_posture_drift",
                     "drifted_keys": pp_result["drifted_keys"], "vocal": vocal}
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
        "candidate_workflow": candidate,
        "bundle_state": bundle_state,
        "emission_signal": er_result,
        "vocal": vocal,
    }


VOCAL_PLAN_TEMPLATE_PATH = SKILL_ROOT / "references" / "vocal_plan_template.txt"


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
        "vocal": ls.is_vocal(outcome),
        "log_path": "orchestration-log.jsonl",
        "candidate_path": "candidate.json",
        "validation_receipts": validation_receipts(
            SKILL_ROOT, collector_summary, (symphony_permission_posture, emission_readiness)),
        "skill_root": str(SKILL_ROOT.relative_to(SKILL_ROOT.parents[1])),
    }
    if ls.is_vocal(outcome):
        tpl = VOCAL_PLAN_TEMPLATE_PATH.read_text(encoding="utf-8")
        plan = tpl.format(run_id=run_id,
                          events_target=f"<this-repo>/skills/leash_for_symphony/outputs/{run_id}/symphony-events.jsonl")
        (bdir / "vocal_capture_plan.md").write_text(plan, encoding="utf-8")
        manifest["vocal_capture_plan_path"] = "vocal_capture_plan.md"
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
    print(f"emitted bundle: {bdir.relative_to(SKILL_ROOT.parents[1])}  claim={outcome['verdict']}  vocal={ls.is_vocal(outcome)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
