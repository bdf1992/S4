"""0.2 signal — trace_conformity for orchestration_audit.

Loads pfsm_parameters from the collector dataset and exposes a typed
evaluate() entry point per [foundations/zero-four.md:141](../../foundations/zero-four.md#L141):

    evaluate(trace) -> (verdict, confidence, evidence_pointers, gap_record)

verdict is one of: "ready" | "not_ready" | "inconclusive".
confidence is in [0, 1] (max softmax probability).
evidence_pointers names the top contributing features.
gap_record (only on non-ready) names which corpus dimension is too thin.

Verdict logic per [skills/orchestration_audit/0_2_design.md](../0_2_design.md):
- "ready": top class is "0.4" and confidence above READY_THRESHOLD
- "not_ready": top class is in {"candidate", "rejected"}, OR softmax
  uniform within tolerance, OR no positive examples for "0.4" exist
- "inconclusive": top class is a non-0.4 success class
"""
from __future__ import annotations

import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PARAMS = REPO / "skills" / "orchestration_audit" / "datasets" / "pfsm_parameters.jsonl"
ACTIVATIONS = REPO / "skills" / "orchestration_audit" / "datasets" / "orchestration_activations.jsonl"
HONESTY = REPO / "skills" / "orchestration_audit" / "datasets" / "decision_point_honesty.jsonl"

READY_THRESHOLD = 0.5
UNIFORM_TOLERANCE = 0.05  # if max softmax prob is within this of uniform, treat as not_ready


def _load_params() -> dict | None:
    if not PARAMS.is_file():
        return None
    line = next((l for l in PARAMS.read_text(encoding="utf-8").splitlines() if l.strip()), None)
    return json.loads(line)["value"] if line else None


def _load_jsonl(p: Path) -> list[dict]:
    if not p.is_file():
        return []
    return [json.loads(l)["value"] for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _featurize(trace: list[dict], feat_names: list[str]) -> list[float]:
    sk = trace[0].get("skill_id", "") if trace else ""
    out: list[float] = []
    for name in feat_names:
        if name == "bias":
            out.append(1.0)
        elif name.startswith("skill:"):
            out.append(1.0 if name[6:] == sk else 0.0)
        elif name.startswith("decision:"):
            out.append(float(sum(1 for a in trace if a.get("decision_id") == name[9:])))
        elif name.startswith("fence:"):
            out.append(float(sum(1 for a in trace if a.get("fence_id") == name[6:])))
        else:
            out.append(0.0)
    return out


def _softmax(z: list[float]) -> list[float]:
    m = max(z)
    e = [math.exp(x - m) for x in z]
    s = sum(e)
    return [x / s for x in e]


def _gap_record(params: dict, trace: list[dict]) -> dict:
    """Name what the corpus is missing relative to a "ready" verdict."""
    acts = _load_jsonl(ACTIVATIONS)
    honesty = _load_jsonl(HONESTY)
    classes = params["classes"]
    class_counts: dict[str, int] = {c: 0 for c in classes}
    seen_runs: set[tuple[str, str]] = set()
    for a in acts:
        k = (a.get("skill_id", ""), a.get("run_id", ""))
        if k in seen_runs:
            continue
        seen_runs.add(k)
        cl = a.get("run_claim", "")
        if cl in class_counts:
            class_counts[cl] += 1
    runs_with_04 = class_counts.get("0.4", 0)
    monotone = sum(1 for h in honesty if h.get("branch_diversity") == 1)
    return {
        "trace_length": len(trace),
        "training_runs": params["training_runs"],
        "runs_with_claim_0_4_in_corpus": runs_with_04,
        "monotone_tuples": monotone,
        "total_tuples": len(honesty),
        "runs_per_class_in_corpus": class_counts,
        "missing_target_class": "0.4" if runs_with_04 == 0 else None,
    }


def _top_evidence(params: dict, x: list[float], top_class: int, k: int = 5) -> list[dict]:
    feats = params["feature_names"]
    W = params["weights"][top_class]
    contribs = [(feats[i], W[i] * x[i]) for i in range(len(feats)) if x[i] != 0.0]
    contribs.sort(key=lambda t: abs(t[1]), reverse=True)
    return [{"feature": f, "contribution": round(c, 4)} for f, c in contribs[:k]]


def evaluate(trace: list[dict]) -> dict:
    """Return {verdict, confidence, evidence_pointers, gap_record}."""
    params = _load_params()
    if params is None:
        return {
            "verdict": "not_ready",
            "confidence": 0.0,
            "evidence_pointers": [],
            "gap_record": {"missing": "pfsm_parameters dataset not present; run collectors.pfsm_parameters first"},
        }
    feats = params["feature_names"]
    classes = params["classes"]
    W = params["weights"]
    x = _featurize(trace, feats)
    logits = [sum(W[c][f] * x[f] for f in range(len(feats))) for c in range(len(classes))]
    probs = _softmax(logits)
    top_idx = probs.index(max(probs))
    top_cls = classes[top_idx]
    conf = probs[top_idx]
    uniform = 1.0 / len(classes)
    near_uniform = (conf - uniform) < UNIFORM_TOLERANCE

    if top_cls == "0.4" and conf >= READY_THRESHOLD:
        verdict = "ready"
    elif near_uniform or top_cls in ("candidate", "rejected"):
        verdict = "not_ready"
    else:
        verdict = "inconclusive"

    out = {
        "verdict": verdict,
        "confidence": round(conf, 4),
        "top_class": top_cls,
        "class_probabilities": {c: round(probs[i], 4) for i, c in enumerate(classes)},
        "evidence_pointers": _top_evidence(params, x, top_idx),
    }
    if verdict != "ready":
        out["gap_record"] = _gap_record(params, trace)
    return out
