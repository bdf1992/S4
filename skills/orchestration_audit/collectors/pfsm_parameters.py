"""Foundation 2 collector — fits a feature-bag linear softmax classifier
by deterministic SGD on the activations corpus and emits one
pfsm_parameters data point containing the fitted weights.

This is the v0 implementation of the architecture committed at
[skills/orchestration_audit/0_2_design.md](../0_2_design.md): a small
gradient-fitted graph (features = state-presence indicators; output
layer = run_claim softmax). v1 can extend to per-skill heads and real
PFSM transition weights when the corpus supports them.

Determinism: zero `random` use; weights initialized from a SHA-256
expansion of a fixed seed; SGD over a fixed iteration count with no
shuffling; same source_state -> byte-identical weights.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

from skills.orchestration_audit.lib import data_point as dp

REPO = Path(__file__).resolve().parents[3]
ACTIVATIONS = REPO / "skills" / "orchestration_audit" / "datasets" / "orchestration_activations.jsonl"
DATASET = REPO / "skills" / "orchestration_audit" / "datasets" / "pfsm_parameters.jsonl"

COLLECTOR_ID = "pfsm_parameters"
KIND = "pfsm_parameters"
VALUE_SCHEMA = {
    "type": "object",
    "required": [
        "feature_names", "classes", "weights", "training_iterations",
        "learning_rate", "l2", "seed", "training_runs", "final_loss",
    ],
}
INPUTS = ["skills/orchestration_audit/datasets/orchestration_activations.jsonl"]

LEARNING_RATE = 0.05
L2 = 0.01
ITERATIONS = 500
SEED = 42
CLASSES = ["candidate", "healthy", "aggregated", "unleashed", "rejected", "0.4"]


def _activations() -> list[dict]:
    if not ACTIVATIONS.is_file():
        return []
    return [json.loads(l)["value"]
            for l in ACTIVATIONS.read_text(encoding="utf-8").splitlines() if l.strip()]


def _runs(acts: list[dict]) -> list[tuple[list[dict], str]]:
    by_run: dict[tuple[str, str], list[dict]] = {}
    for a in acts:
        by_run.setdefault((a["skill_id"], a["run_id"]), []).append(a)
    return [(sorted(v, key=lambda x: x["sequence_index"]), v[0]["run_claim"])
            for _, v in sorted(by_run.items())]


def _vocab(acts: list[dict]) -> tuple[list[str], list[str], list[str]]:
    return (sorted({a["skill_id"] for a in acts}),
            sorted({a["decision_id"] for a in acts}),
            sorted({a["fence_id"] for a in acts}))


def _feat_names(skills: list[str], decisions: list[str], fences: list[str]) -> list[str]:
    return ([f"skill:{s}" for s in skills]
            + [f"decision:{d}" for d in decisions]
            + [f"fence:{f}" for f in fences]
            + ["bias"])


def _featurize(trace: list[dict], skills: list[str], decisions: list[str], fences: list[str]) -> list[float]:
    sk = trace[0]["skill_id"] if trace else ""
    return ([1.0 if s == sk else 0.0 for s in skills]
            + [float(sum(1 for a in trace if a["decision_id"] == d)) for d in decisions]
            + [float(sum(1 for a in trace if a["fence_id"] == f)) for f in fences]
            + [1.0])


def _det_init(n_feat: int, n_cls: int, seed: int) -> list[list[float]]:
    out = [[0.0] * n_feat for _ in range(n_cls)]
    h = hashlib.sha256(str(seed).encode()).digest()
    idx = 0
    for c in range(n_cls):
        for f in range(n_feat):
            out[c][f] = (h[idx % len(h)] / 255.0 - 0.5) * 0.1
            idx += 1
            if idx % len(h) == 0:
                h = hashlib.sha256(h).digest()
    return out


def _softmax(z: list[float]) -> list[float]:
    m = max(z)
    e = [math.exp(x - m) for x in z]
    s = sum(e)
    return [x / s for x in e]


def _train(features: list[list[float]], labels: list[int], n_cls: int) -> tuple[list[list[float]], float]:
    n_feat = len(features[0])
    W = _det_init(n_feat, n_cls, SEED)
    final_loss = 0.0
    for it in range(ITERATIONS):
        total_loss = 0.0
        for x, y in zip(features, labels):
            logits = [sum(W[c][f] * x[f] for f in range(n_feat)) for c in range(n_cls)]
            probs = _softmax(logits)
            total_loss -= math.log(max(probs[y], 1e-12))
            for c in range(n_cls):
                err = probs[c] - (1.0 if c == y else 0.0)
                for f in range(n_feat):
                    W[c][f] -= LEARNING_RATE * (err * x[f] + L2 * W[c][f])
        final_loss = total_loss / max(len(features), 1)
    return W, final_loss


def compute_source_state() -> str:
    h = hashlib.sha256()
    if ACTIVATIONS.is_file():
        h.update(b"activations\0")
        h.update(hashlib.sha256(ACTIVATIONS.read_bytes()).digest())
    h.update(f"\0lr={LEARNING_RATE}\0l2={L2}\0it={ITERATIONS}\0seed={SEED}".encode())
    return "sha256:" + h.hexdigest()[:32]


def _collector_pointer() -> dict:
    return {
        "kind": "collector", "target": {"collector_id": COLLECTOR_ID},
        "resolver": "collector_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved", "last_payload": None, "last_reason": None,
    }


def collect(source_state: str) -> list[dict]:
    acts = _activations()
    if not acts:
        return []
    skills, decisions, fences = _vocab(acts)
    runs = _runs(acts)
    feat_names = _feat_names(skills, decisions, fences)
    features = [_featurize(t, skills, decisions, fences) for t, _ in runs]
    labels = [CLASSES.index(c) if c in CLASSES else CLASSES.index("candidate") for _, c in runs]
    W, final_loss = _train(features, labels, len(CLASSES))
    value = {
        "feature_names": feat_names,
        "classes": list(CLASSES),
        "weights": W,
        "training_iterations": ITERATIONS,
        "learning_rate": LEARNING_RATE,
        "l2": L2,
        "seed": SEED,
        "training_runs": len(runs),
        "final_loss": round(final_loss, 6),
    }
    return [dp.make_data_point(
        collector_id=COLLECTOR_ID, kind=KIND, value=value,
        source_state=source_state, collector_pointer=_collector_pointer(),
    )]


def verify(data_point: dict) -> tuple[str, str]:
    acts = _activations()
    if not acts:
        return "dangling", "no_activations"
    skills, decisions, fences = _vocab(acts)
    runs = _runs(acts)
    if data_point["value"]["training_runs"] != len(runs):
        return "dangling", "run_count_drift"
    feat_names = _feat_names(skills, decisions, fences)
    if data_point["value"]["feature_names"] != feat_names:
        return "dangling", "vocab_drift"
    return "live", "match"


if __name__ == "__main__":
    ss = compute_source_state()
    dps = collect(ss)
    invalid = [(d, r) for d in dps for ok, r in [dp.validate(d)] if not ok]
    if invalid:
        for d, r in invalid:
            print(f"INVALID {d.get('id')}: {r}", file=sys.stderr)
        sys.exit(1)
    dp.write_jsonl(DATASET, dps)
    DATASET.with_suffix(".source_state").write_text(ss + "\n", encoding="utf-8")
    n = dps[0]["value"] if dps else None
    print(f"pfsm_parameters: {len(dps)} data point -> {DATASET.relative_to(REPO)}")
    if n:
        print(f"  trained on {n['training_runs']} runs, {len(n['feature_names'])} features, "
              f"{len(n['classes'])} classes, final_loss={n['final_loss']}")
    print(f"source_state: {ss}")
