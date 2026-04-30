"""0.3 orchestration entry point for the claim_audit skill.

Runs the markdown_claims collector, persists its output, fits the
claim_health signal on that dataset, evaluates an optional query, and
emits a bundle directory containing the stats report, the orchestration
log, and a manifest enumerating every component depended on.

Decision points are declared at module top so verify.py can structurally
check that the source consults exactly these fences in this order.

Usage:
  python -m skills.claim_audit.orchestrate                    # global stats
  python -m skills.claim_audit.orchestrate query.json         # filtered query
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .collectors import markdown_claims
from .lib import data_point as dp
from .signals import claim_health

DECISION_POINTS = [
    ("dataset_present", "markdown_claims"),
    ("claim_health_fit", "claim_health"),
]

COLLECTORS = (markdown_claims,)
SKILL_ROOT = Path(__file__).resolve().parent
DATASETS = SKILL_ROOT / "datasets"
OUTPUTS = SKILL_ROOT / "outputs"

DEFAULT_QUERY: dict = {}


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
    rows = dp.read_jsonl(DATASETS / "markdown_claims.jsonl")
    branch1 = "present" if rows else "missing"
    log.append(_decision("dataset_present", "markdown_claims",
                         input_payload={"row_count": len(rows)},
                         result={"verdict": branch1},
                         branch=branch1))
    if branch1 == "missing":
        return log, {"verdict": "no_data", "reason": "markdown_claims dataset empty"}
    fitted = claim_health.fit(rows)
    result = claim_health.evaluate(query, fitted=fitted, training_rows=rows)
    log.append(_decision("claim_health_fit", "claim_health",
                         input_payload=query, result={"verdict": result["verdict"],
                         "matching_count": result.get("matching_count")},
                         branch=result["verdict"]))
    return log, {"verdict": result["verdict"], "query": query, "stats": fitted,
                 "matching_count": result.get("matching_count"),
                 "matching_rows": result.get("matching_rows", [])}


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
    print(f"  total links: {stats.get('total', 0)}")
    print(f"  internal:    {stats.get('internal', 0)}")
    print(f"  live:        {stats.get('live', 0)}")
    print(f"  dangling:    {stats.get('dangling', 0)}")
    print(f"  unverified:  {stats.get('unverified_anchor', 0)}  (section anchors — punted)")
    print(f"  external:    {stats.get('external', 0)}")
    lr = stats.get("live_ratio")
    if lr is not None:
        print(f"  live_ratio (live / internal): {lr:.3f}")
    print("  by_receipt:")
    for r, c in sorted(stats.get("by_receipt", {}).items()):
        print(f"    {r:22s} {c}")
    worst = sorted(((sum(c.get(k, 0) for k in ("dangling_file", "dangling_line")), s)
                    for s, c in stats.get("by_source", {}).items()), reverse=True)
    worst = [(d, s) for d, s in worst if d > 0][:10]
    if worst:
        print("  top dangling sources:")
        for d, s in worst:
            print(f"    {d:3d}  {s}")
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
