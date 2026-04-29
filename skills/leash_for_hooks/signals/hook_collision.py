"""0.2 signal — hook_collision.

Question answered: does a candidate hook duplicate / shadow an existing
one in the live hook_config dataset?

Fitting: walks the hook_config dataset; the fitted parameter is the set
of (event, matcher, command_hash) tuples observed. Re-fitting is
deterministic and is itself a 0.1 program.

Probe set: two synthetic inputs whose expected verdicts are recorded as
literals; verify.py runs the probes against the signal to confirm
fit-time behavior holds at verification time.
"""
from __future__ import annotations

import hashlib
from typing import Any

SIGNAL_ID = "hook_collision"
TRAINING_DATASET_KIND = "hook_config"
VERDICT_ENUM = ("collides", "clear")


def fit(training_rows: list[dict]) -> set[tuple[str, str, str]]:
    """Returns the set of (event, matcher, command_hash) tuples observed
    in the training dataset (one entry per hook_config data point)."""
    out: set[tuple[str, str, str]] = set()
    for r in training_rows:
        v = r.get("value", {})
        out.add((v.get("event", ""), v.get("matcher", ""), v.get("command_hash", "")))
    return out


def _hash_command(cmd: str) -> str:
    return "sha256:" + hashlib.sha256(cmd.encode()).hexdigest()[:16]


def evaluate(candidate: dict, *, fitted_tuples: set, training_rows: list[dict]) -> dict:
    """Returns {verdict, confidence, evidence_pointers}."""
    cand_tuple = (candidate.get("event", ""), candidate.get("matcher", ""),
                  _hash_command(candidate.get("command", "")))
    if cand_tuple in fitted_tuples:
        evidence = [
            {"kind": "data_point", "target": {"dp_id": r["id"]},
             "resolver": "data_point_resolver"}
            for r in training_rows
            if (r["value"].get("event"), r["value"].get("matcher"),
                r["value"].get("command_hash")) == cand_tuple
        ]
        return {"verdict": "collides", "confidence": 1.0, "evidence_pointers": evidence}
    confidence = min(1.0, len(training_rows) / 5.0)
    return {"verdict": "clear", "confidence": confidence, "evidence_pointers": []}


PROBES: list[dict] = [
    {
        "name": "exact_collision",
        "training": [{"id": "hook_config:probe1", "value": {
            "event": "PreToolUse", "matcher": "Bash",
            "command_hash": _hash_command("echo hi"),
        }}],
        "candidate": {"event": "PreToolUse", "matcher": "Bash", "command": "echo hi"},
        "expected_verdict": "collides",
    },
    {
        "name": "novel_candidate",
        "training": [{"id": "hook_config:probe1", "value": {
            "event": "PreToolUse", "matcher": "Bash",
            "command_hash": _hash_command("echo hi"),
        }}],
        "candidate": {"event": "Stop", "matcher": "*", "command": "echo bye"},
        "expected_verdict": "clear",
    },
]


def run_probes() -> list[dict]:
    out = []
    for probe in PROBES:
        fitted = fit(probe["training"])
        result = evaluate(probe["candidate"],
                          fitted_tuples=fitted, training_rows=probe["training"])
        out.append({"name": probe["name"], "expected": probe["expected_verdict"],
                    "actual": result["verdict"],
                    "pass": result["verdict"] == probe["expected_verdict"]})
    return out
