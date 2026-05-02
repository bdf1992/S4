"""0.2 signal — regime_distribution.

Question answered: across the regime_classification dataset, how many
artifacts sit at each regime, each kind, and within each skill? Is the
floor (0.1 + 0.2 substrate) growing relative to the 0.3 free-write
share?

Fitting: walks the training dataset and computes aggregate counts. The
fitted parameter is a stats dict; re-fitting is deterministic and is
itself a 0.1 program.

Probe set: small synthetic datasets with known expected counts;
verify.py runs the probes against the signal to confirm fit-time
behavior holds at verification time.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

SIGNAL_ID = "regime_distribution"
TRAINING_DATASET_KIND = "regime_classification"
VERDICT_ENUM = ("aggregated", "no_data")

REGIMES = ("bedrock", "0.0", "0.1", "0.2", "0.3", "unclassified")


def _skill_of(path: str) -> str:
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "skills":
        return parts[1]
    if len(parts) >= 1 and parts[0] == "foundations":
        return "_foundations"
    return "_root"


def fit(training_rows: list[dict]) -> dict:
    by_regime: Counter = Counter()
    by_kind: Counter = Counter()
    by_skill: dict[str, Counter] = {}
    total = 0
    for r in training_rows:
        v = r.get("value", {})
        regime = v.get("regime", "unclassified")
        kind = v.get("kind", "unknown")
        path = v.get("path", "")
        by_regime[regime] += 1
        by_kind[kind] += 1
        by_skill.setdefault(_skill_of(path), Counter())[regime] += 1
        total += 1
    floor = by_regime.get("0.1", 0) + by_regime.get("0.2", 0)
    ceiling = by_regime.get("0.3", 0)
    floor_ratio = (floor / ceiling) if ceiling > 0 else None
    return {
        "total": total,
        "by_regime": dict(by_regime),
        "by_kind": dict(by_kind),
        "by_skill": {k: dict(c) for k, c in by_skill.items()},
        "floor_ratio": floor_ratio,
    }


def evaluate(query: dict, *, fitted: dict, training_rows: list[dict]) -> dict:
    if fitted["total"] == 0:
        return {"verdict": "no_data", "stats": fitted, "matching_count": 0,
                "evidence_pointers": []}
    matched: list[dict] = []
    for r in training_rows:
        v = r.get("value", {})
        if "regime" in query and v.get("regime") != query["regime"]:
            continue
        if "kind" in query and v.get("kind") != query["kind"]:
            continue
        if "skill" in query and _skill_of(v.get("path", "")) != query["skill"]:
            continue
        matched.append(r)
    evidence = [{"kind": "data_point", "target": {"dp_id": r["id"]},
                 "resolver": "data_point_resolver"} for r in matched[:10]]
    return {"verdict": "aggregated", "stats": fitted,
            "matching_count": len(matched), "matching_paths": [m["value"]["path"] for m in matched],
            "evidence_pointers": evidence}


def _row(path: str, regime: str, kind: str) -> dict:
    return {"id": f"regime_classification:probe-{path.replace('/', '_')}",
            "value": {"path": path, "regime": regime, "kind": kind, "signals": []}}


PROBES: list[dict] = [
    {
        "name": "all_regimes_present",
        "training": [
            _row("foundations/data-point.md", "bedrock", "foundation_spec"),
            _row("skills/x/collectors/c.py", "0.1", "collector"),
            _row("skills/x/signals/s.py", "0.2", "signal"),
            _row("skills/x/orchestrate.py", "0.3", "orchestration"),
            _row("CLAUDE.md", "0.0", "harness_root"),
        ],
        "query": {},
        "expected_verdict": "aggregated",
        "expected_total": 5,
        "expected_by_regime": {"bedrock": 1, "0.1": 1, "0.2": 1, "0.3": 1, "0.0": 1},
        "expected_floor_ratio": 2.0,
    },
    {
        "name": "filter_by_regime",
        "training": [
            _row("skills/x/collectors/a.py", "0.1", "collector"),
            _row("skills/x/collectors/b.py", "0.1", "collector"),
            _row("skills/x/orchestrate.py", "0.3", "orchestration"),
        ],
        "query": {"regime": "0.1"},
        "expected_verdict": "aggregated",
        "expected_matching_count": 2,
    },
    {
        "name": "empty_dataset",
        "training": [],
        "query": {},
        "expected_verdict": "no_data",
        "expected_total": 0,
    },
]


def _check_probe(probe: dict, fitted: dict, result: dict) -> tuple[bool, dict]:
    checks: dict[str, bool] = {}
    checks["verdict"] = result["verdict"] == probe["expected_verdict"]
    if "expected_total" in probe:
        checks["total"] = fitted["total"] == probe["expected_total"]
    if "expected_by_regime" in probe:
        checks["by_regime"] = fitted["by_regime"] == probe["expected_by_regime"]
    if "expected_floor_ratio" in probe:
        checks["floor_ratio"] = fitted["floor_ratio"] == probe["expected_floor_ratio"]
    if "expected_matching_count" in probe:
        checks["matching_count"] = result.get("matching_count") == probe["expected_matching_count"]
    return all(checks.values()), checks


def run_probes() -> list[dict]:
    out: list[dict] = []
    for probe in PROBES:
        fitted = fit(probe["training"])
        result = evaluate(probe["query"], fitted=fitted, training_rows=probe["training"])
        ok, checks = _check_probe(probe, fitted, result)
        out.append({"name": probe["name"], "expected": probe["expected_verdict"],
                    "actual": result["verdict"], "checks": checks, "pass": ok})
    return out
