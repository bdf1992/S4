"""Walks the skills/ directory and emits one skill_without_verifier
data point per skill that has a SKILL.md but no verify.py.

A skill with SKILL.md is making a structured claim about itself (it
has a name, a purpose, components). A 0.4 bundle, per zero-four.md,
must carry a verify.py that walks itself and exits 0 iff every rung
is present and every pointer is live. A skill claiming structure
without a verifier is making promises it cannot self-check; that is
a measured floor gap, and the closure is a proposal for a verify.py
that handles that specific skill's bundle shape.

Not every skill aspires to be a 0.4 bundle (renderer skills, prior-
art skills predating this experiment). The collector measures; the
operator-approval signal decides which gaps warrant proposals.

This collector is itself 0.1: deterministic, no LLM, declared inputs.
Its source_state hashes the SKILL.md / verify.py presence map across
skills/*/, so changes in skill structure produce a new source_state.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..lib import data_point as dp
from ..lib import pointer as ptr

REPO_ROOT = Path(__file__).resolve().parents[3]

COLLECTOR_ID = "skill_without_verifier"
KIND = "skill_without_verifier"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["skill_pointer", "looked_for"],
    "properties": {
        "skill_pointer": {"type": "object"},
        "looked_for": {"type": "array", "items": {"type": "string"}},
    },
}
INPUTS = ["skills/*/SKILL.md", "skills/*/verify.py"]


def _skill_dirs() -> list[Path]:
    skills_root = REPO_ROOT / "skills"
    if not skills_root.is_dir():
        return []
    return sorted(d for d in skills_root.iterdir()
                  if d.is_dir() and (d / "SKILL.md").is_file())


def compute_source_state() -> str:
    h = hashlib.sha256()
    for d in _skill_dirs():
        rel = d.relative_to(REPO_ROOT).as_posix()
        h.update(rel.encode())
        h.update(b"\0")
        h.update(b"1" if (d / "verify.py").is_file() else b"0")
        h.update(b"\0")
    return "sha256:" + h.hexdigest()


def _collector_pointer() -> dict:
    return ptr.make_unresolved(
        kind="collector",
        target={"collector_id": COLLECTOR_ID},
        resolver="collector_resolver",
    )


def _skill_pointer(skill_rel_path: str) -> dict:
    return ptr.make_unresolved(
        kind="file_path",
        target={"path": skill_rel_path},
        resolver="file_path_resolver",
    )


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    out: list[dict] = []
    for d in _skill_dirs():
        if (d / "verify.py").is_file():
            continue
        rel = d.relative_to(REPO_ROOT).as_posix()
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND,
            value={
                "skill_pointer": _skill_pointer(rel),
                "looked_for": [f"{rel}/verify.py"],
            },
            source_state=source_state, collector_pointer=cp,
        ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    rel = data_point["value"]["skill_pointer"]["target"]["path"]
    skill_dir = REPO_ROOT / rel
    if not (skill_dir / "SKILL.md").is_file():
        return "dangling", "skill_no_longer_present"
    if (skill_dir / "verify.py").is_file():
        return "dangling", "verifier_now_present"
    return "live", "still_missing_verifier"
