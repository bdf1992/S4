"""0.2 signal — slash_command_collision.

Question answered: does a candidate slash-command name shadow an
existing user-authored command in the live slash_command_config dataset?

Fitting: walks the slash_command_config dataset; the fitted parameter is
the set of name_hash values observed. Re-fitting is deterministic and
itself a 0.1 program.

Probe set: two synthetic inputs whose expected verdicts are recorded as
literals; verify.py runs the probes against the signal to confirm
fit-time behavior holds at verification time.

Note: this signal is for collisions WITHIN the user/project corpus.
Collisions against the reserved-names taxonomy are handled upstream as a
0.1 dataset-membership decision (name_validity)."""
from __future__ import annotations

import hashlib

SIGNAL_ID = "slash_command_collision"
TRAINING_DATASET_KIND = "slash_command_config"
VERDICT_ENUM = ("collides", "clear")


def fit(training_rows: list[dict]) -> set[str]:
    """Returns the set of name_hash values observed in the training
    dataset (one entry per slash_command_config data point)."""
    out: set[str] = set()
    for r in training_rows:
        v = r.get("value", {})
        out.add(v.get("name_hash", ""))
    return out


def _hash_name(name: str) -> str:
    return "sha256:" + hashlib.sha256(name.encode()).hexdigest()[:16]


def evaluate(candidate: dict, *, fitted_hashes: set,
             training_rows: list[dict]) -> dict:
    """Returns {verdict, confidence, evidence_pointers}."""
    cand_hash = _hash_name(candidate.get("name", "").lower())
    if cand_hash in fitted_hashes:
        evidence = [
            {"kind": "data_point", "target": {"dp_id": r["id"]},
             "resolver": "data_point_resolver"}
            for r in training_rows
            if r["value"].get("name_hash") == cand_hash
        ]
        return {"verdict": "collides", "confidence": 1.0,
                "evidence_pointers": evidence}
    confidence = min(1.0, len(training_rows) / 5.0)
    return {"verdict": "clear", "confidence": confidence,
            "evidence_pointers": []}


PROBES: list[dict] = [
    {
        "name": "exact_collision",
        "training": [{"id": "slash_command_config:probe1", "value": {
            "name": "deploy", "name_hash": _hash_name("deploy"),
        }}],
        "candidate": {"name": "deploy"},
        "expected_verdict": "collides",
    },
    {
        "name": "novel_candidate",
        "training": [{"id": "slash_command_config:probe1", "value": {
            "name": "deploy", "name_hash": _hash_name("deploy"),
        }}],
        "candidate": {"name": "rollback"},
        "expected_verdict": "clear",
    },
]


def run_probes() -> list[dict]:
    out = []
    for probe in PROBES:
        fitted = fit(probe["training"])
        result = evaluate(probe["candidate"], fitted_hashes=fitted,
                          training_rows=probe["training"])
        out.append({"name": probe["name"], "expected": probe["expected_verdict"],
                    "actual": result["verdict"],
                    "pass": result["verdict"] == probe["expected_verdict"]})
    return out
