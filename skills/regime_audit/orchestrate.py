"""0.3 orchestration entry point for the regime_audit skill.

Runs the regime_classification collector, persists its output, fits the
regime_distribution signal on that dataset, evaluates an optional query,
and emits a bundle directory containing the stats report, the
orchestration log, and a manifest enumerating every component depended
on.

Decision points are declared at module top so verify.py can structurally
check that the source consults exactly these fences in this order.

Usage:
  python -m skills.regime_audit.orchestrate                  # global stats
  python -m skills.regime_audit.orchestrate query.json        # filtered query
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .collectors import regime_classification
from .lib import data_point as dp
from .signals import regime_distribution

DECISION_POINTS = [
    ("dataset_present", "regime_classification"),  # 0.1 dataset existence
    ("distribution_fit", "regime_distribution"),   # 0.2 signal
]

COLLECTORS = (regime_classification,)
SKILL_ROOT = Path(__file__).resolve().parent
DATASETS = SKILL_ROOT / "datasets"
OUTPUTS = SKILL_ROOT / "outputs"

DEFAULT_QUERY: dict = {}  # empty query → return global stats


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


def evaluate_query(query: dict) -> tuple[list[dict], dict]:
    log: list[dict] = []
    rows = dp.read_jsonl(DATASETS / "regime_classification.jsonl")
    branch1 = "present" if rows else "missing"
    log.append(_decision("dataset_present", "regime_classification",
                         input_payload={"row_count": len(rows)},
                         result={"verdict": branch1},
                         branch=branch1))
    if branch1 == "missing":
        return log, {"verdict": "no_data", "reason": "regime_classification dataset empty"}
    fitted = regime_distribution.fit(rows)
    result = regime_distribution.evaluate(query, fitted=fitted, training_rows=rows)
    log.append(_decision("distribution_fit", "regime_distribution",
                         input_payload=query, result={"verdict": result["verdict"],
                         "matching_count": result.get("matching_count")},
                         branch=result["verdict"]))
    return log, {"verdict": result["verdict"], "query": query, "stats": fitted,
                 "matching_count": result.get("matching_count"),
                 "matching_paths": result.get("matching_paths", [])}


def emit_bundle(collector_summary: dict, log: list[dict], outcome: dict) -> Path:
    run_id = "run-" + dp.content_hash({"log": log, "outcome": outcome})
    bdir = OUTPUTS / run_id
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / "stats.json").write_text(json.dumps(outcome, indent=2, sort_keys=True), encoding="utf-8")
    dp.write_jsonl(bdir / "orchestration-log.jsonl", log)
    manifest = {
        "claim": outcome["verdict"],
        "collectors": collector_summary,
        "decision_points": [list(x) for x in DECISION_POINTS],
        "log_path": "orchestration-log.jsonl",
        "stats_path": "stats.json",
        "skill_root": str(SKILL_ROOT.relative_to(SKILL_ROOT.parents[1])),
    }
    (bdir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return bdir


def _print_stats(outcome: dict) -> None:
    stats = outcome.get("stats", {})
    print(f"  total artifacts: {stats.get('total', 0)}")
    print("  by regime:")
    for r in ("bedrock", "0.0", "0.1", "0.2", "0.3", "unclassified"):
        if r in stats.get("by_regime", {}):
            print(f"    {r:14s} {stats['by_regime'][r]}")
    fr = stats.get("floor_ratio")
    if fr is not None:
        print(f"  floor_ratio (0.1+0.2)/0.3: {fr:.2f}")
    print("  by kind:")
    for k, c in sorted(stats.get("by_kind", {}).items()):
        print(f"    {k:22s} {c}")
    print("  by skill:")
    for s, counts in sorted(stats.get("by_skill", {}).items()):
        bits = ", ".join(f"{r}={n}" for r, n in sorted(counts.items()))
        print(f"    {s:30s} {bits}")
    if outcome.get("matching_count") is not None and outcome.get("query"):
        print(f"  query {outcome['query']}: matched {outcome['matching_count']} of {stats.get('total', 0)}")


def main() -> int:
    query = DEFAULT_QUERY
    if len(sys.argv) > 1:
        query = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    summary = run_all_collectors()
    log, outcome = evaluate_query(query)
    bdir = emit_bundle(summary, log, outcome)
    print(f"emitted bundle: {bdir.relative_to(SKILL_ROOT.parents[1])}  claim={outcome['verdict']}")
    _print_stats(outcome)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
