"""Draft preview of skills/subprotocol-for-claude-code/verify.py post-parameterization."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bundle_verifier as bv  # production: from skills.bundle_verifier import bundle_verifier as bv

COLLECTOR_ID = "subprotocol_for_claude_code_verifier"
SKILL_REL = "skills/subprotocol-for-claude-code"
PRESENCE: list[str] = [
    "SKILL.md", "overlay.md",
    "references/domain-configuration-schema.md",
    "references/domain-configuration.yaml",
    "references/translation-map.md",
]
PYTHON_AUDIT: list[str] = ["scripts/setup-interview.py", "scripts/sync.py"]

KIND = bv.KIND
VALUE_SCHEMA = bv.VALUE_SCHEMA
INPUTS = bv.compute_inputs(SKILL_REL, PRESENCE, PYTHON_AUDIT)


def collect(source_state: str) -> list[dict]:
    return bv.collect(COLLECTOR_ID, SKILL_REL, PRESENCE, PYTHON_AUDIT, source_state)


def verify(data_point: dict) -> tuple[str, str]:
    return bv.verify(data_point)
