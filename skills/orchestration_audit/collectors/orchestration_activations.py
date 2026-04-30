"""Foundation 2 collector — emits one data point per 0.3 fence consultation.

Walks every skills/*/outputs/run-*/orchestration-log.jsonl plus its sibling
manifest.json, emits one orchestration_activation per logged record. The
manifest's `claim` is attached as run-level context.

This corpus is the dataset 0.3 cannot self-supply: an independent 0.1
program measuring 0.3's activations of 0.1 fences. It becomes the input
for the honesty auditor (Prereq B) and the first real 0.2 trace-conformity
model. The values stored are *summaries* of each activation (decision_id,
fence_id, branch_taken, verdict/confidence, key-sets of payload/result);
the full payloads remain in the source log files, which the
collector_pointer + source_state re-resolve to.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from skills.orchestration_audit.lib import data_point as dp

COLLECTOR_ID = "orchestration_activations"
KIND = "orchestration_activation"
VALUE_SCHEMA = {
    "type": "object",
    "required": [
        "run_id", "skill_id", "sequence_index", "decision_id", "fence_id",
        "branch_taken", "input_keys", "result_keys", "verdict", "confidence",
        "run_claim",
    ],
    "properties": {
        "run_id": {"type": "string"},
        "skill_id": {"type": "string"},
        "sequence_index": {"type": "integer"},
        "decision_id": {"type": "string"},
        "fence_id": {"type": "string"},
        "branch_taken": {"type": "string"},
        "input_keys": {"type": "array", "items": {"type": "string"}},
        "result_keys": {"type": "array", "items": {"type": "string"}},
        "verdict": {"type": ["string", "null"]},
        "confidence": {"type": ["number", "null"]},
        "run_claim": {"type": "string"},
    },
}
INPUTS = [
    "skills/*/outputs/run-*/orchestration-log.jsonl",
    "skills/*/outputs/run-*/manifest.json",
]
REPO = Path(__file__).resolve().parents[3]
DATASET = REPO / "skills" / "orchestration_audit" / "datasets" / "orchestration_activations.jsonl"


def _runs() -> list[tuple[Path, Path, str, str]]:
    out: list[tuple[Path, Path, str, str]] = []
    for skill in sorted((REPO / "skills").glob("*")):
        out_dir = skill / "outputs"
        if not out_dir.is_dir():
            continue
        for run in sorted(out_dir.glob("run-*")):
            log = run / "orchestration-log.jsonl"
            man = run / "manifest.json"
            if log.is_file() and man.is_file():
                out.append((log, man, skill.name, run.name))
    return out


def compute_source_state() -> str:
    h = hashlib.sha256()
    for log, man, skill, run in _runs():
        h.update(f"{skill}/{run}".encode()); h.update(b"\0")
        h.update(hashlib.sha256(log.read_bytes()).digest())
        h.update(hashlib.sha256(man.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32]


def _collector_pointer() -> dict:
    return {
        "kind": "collector", "target": {"collector_id": COLLECTOR_ID},
        "resolver": "collector_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved", "last_payload": None, "last_reason": None,
    }


def _activations(log: Path, man: Path, skill: str, run: str) -> list[dict]:
    try:
        manifest = json.loads(man.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    claim = manifest.get("claim", "unknown") if isinstance(manifest, dict) else "unknown"
    out: list[dict] = []
    for i, raw in enumerate(log.read_text(encoding="utf-8").splitlines()):
        line = raw.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        payload = rec.get("input_payload")
        result = rec.get("result")
        out.append({
            "run_id": run,
            "skill_id": skill,
            "sequence_index": i,
            "decision_id": str(rec.get("decision_id", "")),
            "fence_id": str(rec.get("fence_id", "")),
            "branch_taken": str(rec.get("branch_taken", "")),
            "input_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
            "result_keys": sorted(result.keys()) if isinstance(result, dict) else [],
            "verdict": result.get("verdict") if isinstance(result, dict) else None,
            "confidence": result.get("confidence") if isinstance(result, dict) else None,
            "run_claim": str(claim),
        })
    return out


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    out: list[dict] = []
    for log, man, skill, run in _runs():
        for v in _activations(log, man, skill, run):
            out.append(dp.make_data_point(
                collector_id=COLLECTOR_ID, kind=KIND, value=v,
                source_state=source_state, collector_pointer=cp,
            ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    v = data_point["value"]
    for log, man, skill, run in _runs():
        if skill != v["skill_id"] or run != v["run_id"]:
            continue
        for c in _activations(log, man, skill, run):
            if c["sequence_index"] == v["sequence_index"]:
                return ("live", "match") if c == v else ("dangling", "value_drift")
        return "dangling", "sequence_missing"
    return "dangling", "run_missing"


if __name__ == "__main__":
    ss = compute_source_state()
    dps = collect(ss)
    bad = [(d, dp.validate(d)) for d in dps]
    invalid = [(d, r) for d, (ok, r) in bad if not ok]
    if invalid:
        for d, r in invalid:
            print(f"INVALID {d.get('id')}: {r}", file=sys.stderr)
        sys.exit(1)
    dp.write_jsonl(DATASET, dps)
    DATASET.with_suffix(".source_state").write_text(ss + "\n", encoding="utf-8")
    print(f"orchestration_activations: {len(dps)} data points -> {DATASET.relative_to(REPO)}")
    print(f"source_state: {ss}")
