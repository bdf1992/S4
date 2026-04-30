"""Draft preview of skills/orchestration_audit/verify.py post-parameterization."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bundle_verifier as bv  # production: from skills.bundle_verifier import bundle_verifier as bv

COLLECTOR_ID = "orchestration_audit_verifier"
SKILL_REL = "skills/orchestration_audit"
PRESENCE: list[str] = [
    "SKILL.md",
    "datasets/orchestration_activations.jsonl",
    "datasets/orchestration_activations.source_state",
]
PYTHON_AUDIT: list[str] = [
    "collectors/orchestration_activations.py",
    "lib/data_point.py",
]

KIND = bv.KIND
VALUE_SCHEMA = bv.VALUE_SCHEMA
INPUTS = bv.compute_inputs(SKILL_REL, PRESENCE, PYTHON_AUDIT)


def collect(source_state: str) -> list[dict]:
    return bv.collect(COLLECTOR_ID, SKILL_REL, PRESENCE, PYTHON_AUDIT, source_state)


def verify(data_point: dict) -> tuple[str, str]:
    return bv.verify(data_point)
