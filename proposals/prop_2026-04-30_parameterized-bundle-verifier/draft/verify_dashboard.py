"""Draft preview of skills/dashboard/verify.py post-parameterization.

Production form: `from skills.bundle_verifier import bundle_verifier as bv`.
Draft uses sibling-module import for runnability before the
skills/bundle_verifier/ landing zone exists.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bundle_verifier as bv  # production: from skills.bundle_verifier import bundle_verifier as bv

COLLECTOR_ID = "dashboard_verifier"
SKILL_REL = "skills/dashboard"
PRESENCE: list[str] = ["SKILL.md"]
PYTHON_AUDIT: list[str] = ["render.py", "snapshot.py", "narrate.py", "html.py"]

KIND = bv.KIND
VALUE_SCHEMA = bv.VALUE_SCHEMA
INPUTS = bv.compute_inputs(SKILL_REL, PRESENCE, PYTHON_AUDIT)


def collect(source_state: str) -> list[dict]:
    return bv.collect(COLLECTOR_ID, SKILL_REL, PRESENCE, PYTHON_AUDIT, source_state)


def verify(data_point: dict) -> tuple[str, str]:
    return bv.verify(data_point)
