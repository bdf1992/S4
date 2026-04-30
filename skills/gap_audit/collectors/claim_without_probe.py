"""Walks claim_audit's md_link dataset and emits one claim_without_probe
data point per md_link record whose receipt is `anchor_unverified` —
i.e., a markdown link whose target file exists but whose section anchor
has no resolver in the live floor.

The gap is mechanical, not judged: claim_audit explicitly punts on
section-anchor verification (kind boundary, see claim_audit/SKILL.md).
Each anchor_unverified record names a specific resolver-capability that
does not yet exist (`resolve:repo_path_section_anchored`). A follow-on
collector that graded section anchors against rendered heading slugs
would close the gap; until one exists, the claim sits with a partial
probe and counts as a measured floor-growth opportunity.

This collector is itself 0.1: deterministic, no LLM, declared inputs.
Its source_state hashes the input dataset files so the gap inventory
is anchored to exactly the version of claim_audit's output it walked.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..lib import data_point as dp
from ..lib import pointer as ptr

REPO_ROOT = Path(__file__).resolve().parents[3]

COLLECTOR_ID = "claim_without_probe"
KIND = "claim_without_probe"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["claim_pointer", "looked_for"],
    "properties": {
        "claim_pointer": {"type": "object"},
        "looked_for": {"type": "array", "items": {"type": "string"}},
    },
}
INPUTS = [
    "skills/claim_audit/datasets/markdown_claims.jsonl",
    "skills/claim_audit/datasets/markdown_claims.source_state",
]

# Map from md_link receipt to the resolver-capability strings whose absence
# makes that receipt a claim-without-probe. Receipts not in this map are
# claims-with-probe — claim_audit's own resolver covers them.
_GAP_RECEIPTS = {
    "anchor_unverified": ["resolve:repo_path_section_anchored"],
}


def compute_source_state() -> str:
    h = hashlib.sha256()
    for rel in INPUTS:
        p = REPO_ROOT / rel
        if not p.exists():
            h.update(b"missing:" + rel.encode())
            continue
        h.update(rel.encode())
        h.update(b"\0")
        h.update(p.read_bytes())
    return "sha256:" + h.hexdigest()


def _collector_pointer() -> dict:
    return ptr.make_unresolved(
        kind="collector",
        target={"collector_id": COLLECTOR_ID},
        resolver="collector_resolver",
    )


def _claim_pointer(md_link_id: str) -> dict:
    return ptr.make_unresolved(
        kind="data_point",
        target={"data_point_id": md_link_id},
        resolver="data_point_resolver",
    )


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    out: list[dict] = []
    dataset_path = REPO_ROOT / INPUTS[0]
    if not dataset_path.exists():
        return out
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        receipt = record.get("value", {}).get("receipt")
        looked_for = _GAP_RECEIPTS.get(receipt)
        if looked_for is None:
            continue
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND,
            value={
                "claim_pointer": _claim_pointer(record["id"]),
                "looked_for": looked_for,
            },
            source_state=source_state, collector_pointer=cp,
        ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    target_id = data_point["value"]["claim_pointer"]["target"]["data_point_id"]
    dataset_path = REPO_ROOT / INPUTS[0]
    if not dataset_path.exists():
        return "dangling", "claim_dataset_missing"
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("id") == target_id:
            if rec.get("value", {}).get("receipt") in _GAP_RECEIPTS:
                return "live", rec["value"]["receipt"]
            return "dangling", "claim_no_longer_a_gap"
    return "dangling", "claim_id_not_in_dataset"
