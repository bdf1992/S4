"""0.2 signal — outcome_5_recurrence.

Question answered: for a given surface_id, has the operator (or agent)
hand-walked ladder discipline against it enough times that recursion-seam
outcome 5 should fire — i.e., a sibling leash for that surface is now
warranted by signal rather than by override?

Consumes `surface_handwalk` data points emitted by
[skills/gap_audit/collectors/surface_handwalk_recurrence.py].

Fitting: aggregates surface_handwalk records into per-surface counts
of distinct artifacts. The fitted parameter is `{surface_id: count}`
plus the threshold `N`. Re-fitting is deterministic and is itself a
0.1 program (no LLM, no time-as-value, no random).

Threshold: `N = 3` for v0. Three independent recurrences is above
single-session noise but cheap enough to act on. Per
[proposals/prop_2026-04-30_leash-for-symphony/README.md] the exact
threshold is "fitted to operator session cadence" — re-tunable later
without changing the signal's shape.

The signal does not act. The operator (or a downstream orchestrator)
decides whether to build the leash on a `fire` verdict. The signal
informs.
"""
from __future__ import annotations

from collections import Counter

SIGNAL_ID = "outcome_5_recurrence"
TRAINING_DATASET_KIND = "surface_handwalk"
VERDICT_ENUM = ("fire", "hold")
THRESHOLD_N = 3


def fit(training_rows: list[dict]) -> dict:
    counts: Counter = Counter()
    seen_artifacts_per_surface: dict[str, set[str]] = {}
    for r in training_rows:
        if r.get("kind") != TRAINING_DATASET_KIND:
            continue
        v = r.get("value", {})
        sid = v.get("surface")
        if not sid:
            continue
        artifact = v.get("artifact_pointer", {}).get("target", {}).get("path", "")
        seen = seen_artifacts_per_surface.setdefault(sid, set())
        if artifact and artifact not in seen:
            seen.add(artifact)
            counts[sid] += 1
    return {"per_surface_counts": dict(counts), "threshold_n": THRESHOLD_N}


def evaluate(candidate_surface: str, *, fitted_params: dict, training_rows: list[dict]) -> dict:
    counts = fitted_params["per_surface_counts"]
    n = fitted_params["threshold_n"]
    c = counts.get(candidate_surface, 0)
    verdict = "fire" if c >= n else "hold"
    evidence = [
        r["value"]["artifact_pointer"]
        for r in training_rows
        if r.get("kind") == TRAINING_DATASET_KIND
        and r.get("value", {}).get("surface") == candidate_surface
    ]
    return {
        "verdict": verdict,
        "confidence": 1.0 if verdict == "fire" else (c / n),
        "count": c,
        "threshold": n,
        "evidence_pointers": evidence,
    }


def _row(surface: str, path: str) -> dict:
    return {"kind": TRAINING_DATASET_KIND, "value": {"surface": surface, "artifact_pointer": {"target": {"path": path}}}}


_BELOW = [_row("x", "a")]
_AT = [_row("x", f"a{i}") for i in range(3)]
_ABOVE = _AT + [_row("x", "a3")]
_DUPS = [_row("x", "same"), _row("x", "same"), _row("x", "same")]

PROBES = (
    ("hold_when_below_threshold",  _BELOW,  "x", "hold"),
    ("fire_at_threshold",          _AT,     "x", "fire"),
    ("fire_above_threshold",       _ABOVE,  "x", "fire"),
    ("hold_for_unknown_surface",   _AT,     "y", "hold"),
    ("hold_when_only_dups_repeat", _DUPS,   "x", "hold"),
)


def run_probes() -> tuple[bool, list[str]]:
    failures: list[str] = []
    for name, rows, surface, expected in PROBES:
        params = fit(rows)
        result = evaluate(surface, fitted_params=params, training_rows=rows)
        if result["verdict"] != expected:
            failures.append(f"{name}: expected {expected}, got {result['verdict']} (count={result['count']})")
    return (not failures), failures
