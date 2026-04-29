"""0.2 signal — emission_readiness.

Question answered: given the bundle state (collectors run, datasets
populated, candidate evaluated by upstream signals), is the corpus dense
enough that the bundle is permitted to stamp itself 0.4 — or only
sub-0.4 candidate?

Fitting: walks an *exemplar* dataset of bundle states previously
considered healthy enough to fire. On first run, the exemplar dataset is
empty; the signal's fit is therefore degenerate and the signal honestly
returns not_ready with gap_record describing what data is missing.

The hyperparameter MIN_EXEMPLARS is declared (not learned). It says the
signal needs at least N exemplar bundle states to consider its fit
non-degenerate. This is the only authored number; the rest is data.

Probe set: synthetic bundle states whose expected verdicts are recorded
as literals.
"""
from __future__ import annotations

SIGNAL_ID = "emission_readiness"
TRAINING_DATASET_KIND = "exemplar_bundle_state"
VERDICT_ENUM = ("ready", "not_ready")
MIN_EXEMPLARS = 3


def fit(training_rows: list[dict]) -> dict:
    if len(training_rows) < MIN_EXEMPLARS:
        return {"degenerate": True, "n_exemplars": len(training_rows),
                "min_required": MIN_EXEMPLARS,
                "min_per_kind": {}}
    counts_per_kind: dict[str, list[int]] = {}
    for ex in training_rows:
        for kind, n in ex.get("value", {}).get("dataset_sizes", {}).items():
            counts_per_kind.setdefault(kind, []).append(n)
    min_per_kind = {k: min(vs) for k, vs in counts_per_kind.items()}
    return {"degenerate": False, "n_exemplars": len(training_rows),
            "min_required": MIN_EXEMPLARS,
            "min_per_kind": min_per_kind}


def evaluate(bundle_state: dict, *, fitted: dict, training_rows: list[dict]) -> dict:
    """Returns {verdict, confidence, evidence_pointers, gap_record}."""
    if fitted.get("degenerate"):
        return {
            "verdict": "not_ready", "confidence": 1.0, "evidence_pointers": [],
            "gap_record": {
                "reason": "insufficient_training_exemplars",
                "have": fitted["n_exemplars"], "need": fitted["min_required"],
                "remediation": "produce additional exemplar_bundle_state data points "
                "(by running the leash on more candidates and recording the bundles "
                "judged healthy) until at least MIN_EXEMPLARS are available",
            },
        }
    sizes = bundle_state.get("dataset_sizes", {})
    shortfalls = {k: (sizes.get(k, 0), need)
                  for k, need in fitted["min_per_kind"].items()
                  if sizes.get(k, 0) < need}
    if shortfalls:
        return {"verdict": "not_ready", "confidence": 1.0, "evidence_pointers": [],
                "gap_record": {"reason": "dataset_shortfall", "shortfalls": shortfalls}}
    if not bundle_state.get("all_collectors_passed", False):
        return {"verdict": "not_ready", "confidence": 1.0, "evidence_pointers": [],
                "gap_record": {"reason": "collector_failures",
                               "details": bundle_state.get("collector_failures", [])}}
    return {"verdict": "ready", "confidence": 1.0, "evidence_pointers": [],
            "gap_record": None}


PROBES: list[dict] = [
    {
        "name": "degenerate_fit_returns_not_ready",
        "training": [],
        "bundle_state": {"dataset_sizes": {"hook_config": 100}, "all_collectors_passed": True},
        "expected_verdict": "not_ready",
    },
    {
        "name": "non_degenerate_with_shortfall_returns_not_ready",
        "training": [
            {"value": {"dataset_sizes": {"hook_config": 5}}},
            {"value": {"dataset_sizes": {"hook_config": 7}}},
            {"value": {"dataset_sizes": {"hook_config": 10}}},
        ],
        "bundle_state": {"dataset_sizes": {"hook_config": 2}, "all_collectors_passed": True},
        "expected_verdict": "not_ready",
    },
    {
        "name": "non_degenerate_clean_returns_ready",
        "training": [
            {"value": {"dataset_sizes": {"hook_config": 5}}},
            {"value": {"dataset_sizes": {"hook_config": 7}}},
            {"value": {"dataset_sizes": {"hook_config": 10}}},
        ],
        "bundle_state": {"dataset_sizes": {"hook_config": 8}, "all_collectors_passed": True},
        "expected_verdict": "ready",
    },
]


def run_probes() -> list[dict]:
    out = []
    for probe in PROBES:
        fitted = fit(probe["training"])
        result = evaluate(probe["bundle_state"], fitted=fitted, training_rows=probe["training"])
        out.append({"name": probe["name"], "expected": probe["expected_verdict"],
                    "actual": result["verdict"],
                    "pass": result["verdict"] == probe["expected_verdict"]})
    return out
