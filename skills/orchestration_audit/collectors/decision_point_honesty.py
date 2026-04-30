"""Foundation 2 collector — measures structural honesty of each (skill, decision, fence) tuple.

For each unique (skill_id, decision_id, fence_id) seen in the activations
corpus (Prereq A), the collector reports four measurements:

1. Where the literal decision_id appears in skills/{skill_id}/**/*.py.
2. Where the literal fence_id appears in the same source.
3. Branch and verdict diversity observed across the corpus's records for
   that tuple (how many distinct branches were taken; how many distinct
   verdicts were seen; which branches were taken under which verdicts).
4. The activation count.

The collector does NOT classify "honest" vs "decorative". That arbitration
is what a downstream 0.2 signal exists to do — the collector measures and
reports. A downstream signal can read these data points and decide that,
e.g., branch_diversity == 1 with verdict_diversity > 1 is evidence of a
decorative consultation.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from skills.orchestration_audit.lib import data_point as dp

COLLECTOR_ID = "decision_point_honesty"
KIND = "decision_point_honesty"
VALUE_SCHEMA = {
    "type": "object",
    "required": [
        "skill_id", "decision_id", "fence_id",
        "decision_id_locations", "fence_id_locations",
        "branch_diversity", "verdict_diversity",
        "branches_per_verdict", "activation_count",
    ],
    "properties": {
        "skill_id": {"type": "string"},
        "decision_id": {"type": "string"},
        "fence_id": {"type": "string"},
        "decision_id_locations": {"type": "array"},
        "fence_id_locations": {"type": "array"},
        "branch_diversity": {"type": "integer"},
        "verdict_diversity": {"type": "integer"},
        "branches_per_verdict": {"type": "object"},
        "activation_count": {"type": "integer"},
    },
}
INPUTS = [
    "skills/orchestration_audit/datasets/orchestration_activations.jsonl",
    "skills/*/**/*.py",
]
REPO = Path(__file__).resolve().parents[3]
ACTIVATIONS = REPO / "skills" / "orchestration_audit" / "datasets" / "orchestration_activations.jsonl"
DATASET = REPO / "skills" / "orchestration_audit" / "datasets" / "decision_point_honesty.jsonl"


def _activations() -> list[dict]:
    if not ACTIVATIONS.is_file():
        return []
    return [json.loads(l)["value"]
            for l in ACTIVATIONS.read_text(encoding="utf-8").splitlines() if l.strip()]


def _skill_pys(skill_id: str) -> list[Path]:
    skill_dir = REPO / "skills" / skill_id
    if not skill_dir.is_dir():
        return []
    return sorted(p for p in skill_dir.rglob("*.py") if "__pycache__" not in p.parts)


def _find_literal(files: list[Path], literal: str) -> list[dict]:
    out: list[dict] = []
    quoted = (f'"{literal}"', f"'{literal}'")
    for f in files:
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), start=1):
            if any(q in line for q in quoted):
                out.append({"file": f.relative_to(REPO).as_posix(), "line": i})
    return out


def compute_source_state() -> str:
    h = hashlib.sha256()
    if ACTIVATIONS.is_file():
        h.update(b"activations\0")
        h.update(hashlib.sha256(ACTIVATIONS.read_bytes()).digest())
    for skill_id in sorted({a["skill_id"] for a in _activations()}):
        for p in _skill_pys(skill_id):
            h.update(p.relative_to(REPO).as_posix().encode()); h.update(b"\0")
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32]


def _collector_pointer() -> dict:
    return {
        "kind": "collector", "target": {"collector_id": COLLECTOR_ID},
        "resolver": "collector_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved", "last_payload": None, "last_reason": None,
    }


def _measure(group: list[dict], skill_id: str, decision_id: str, fence_id: str) -> dict:
    files = _skill_pys(skill_id)
    branches = sorted({a["branch_taken"] for a in group})
    verdicts = sorted({(a["verdict"] or "<null>") for a in group})
    bpv: dict[str, list[str]] = {}
    for a in group:
        v = a["verdict"] or "<null>"
        bpv.setdefault(v, [])
        if a["branch_taken"] not in bpv[v]:
            bpv[v].append(a["branch_taken"])
    return {
        "skill_id": skill_id,
        "decision_id": decision_id,
        "fence_id": fence_id,
        "decision_id_locations": _find_literal(files, decision_id),
        "fence_id_locations": _find_literal(files, fence_id),
        "branch_diversity": len(branches),
        "verdict_diversity": len(verdicts),
        "branches_per_verdict": {v: sorted(bpv[v]) for v in sorted(bpv)},
        "activation_count": len(group),
    }


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for a in _activations():
        groups.setdefault((a["skill_id"], a["decision_id"], a["fence_id"]), []).append(a)
    out: list[dict] = []
    for k in sorted(groups.keys()):
        v = _measure(groups[k], *k)
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND, value=v,
            source_state=source_state, collector_pointer=cp,
        ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    v = data_point["value"]
    group = [a for a in _activations()
             if (a["skill_id"], a["decision_id"], a["fence_id"])
                == (v["skill_id"], v["decision_id"], v["fence_id"])]
    if not group:
        return "dangling", "group_missing"
    cand = _measure(group, v["skill_id"], v["decision_id"], v["fence_id"])
    return ("live", "match") if cand == v else ("dangling", "value_drift")


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
    print(f"decision_point_honesty: {len(dps)} data points -> {DATASET.relative_to(REPO)}")
    print(f"source_state: {ss}")
