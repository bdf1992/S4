"""Walks meeting-notes/ and proposals/**/*.md for files that hand-walk
ladder discipline against a named surface, and emits one
surface_handwalk data point per (file, surface) pair.

A handwalk is evidence that the operator (or agent) is re-deriving
ladder discipline for a surface that has no existing leash skill.
[skills/leash_for_hooks/recursion-seam.md] outcome 5 says: "Every time
the same shape of ad-hoc verification gets re-derived, that recurrence
is the signal that a new leash should formalize it." This collector
counts those recurrences deterministically so a downstream signal
can decide whether a sibling leash is warranted (vs. being built by
override).

Detection criteria, all-of:
  1. File is under meeting-notes/*.md or proposals/**/*.md.
  2. File path is NOT under any excluded_path_prefixes (would be
     the formal leash for that surface, not a handwalk against it).
  3. File path is NOT in excluded_files (auto-generated renders).
  4. File contains >=3 distinct ladder-vocabulary tokens.
  5. File contains >=2 surface-synonym hits for the surface in
     question (single mention is enumeration, not a handwalk).
  6. The surface does NOT already have a `skills/<leash_dir>/`
     directory (already-leashed surfaces are not outcome-5 candidates).

Per (file, surface) pair meeting all six, one data point is emitted.

The closed taxonomy and detection thresholds live in
[skills/gap_audit/references/surface-taxonomy.json] so they are
editable as data and source_state hashes the taxonomy file's bytes
directly.

This collector is itself 0.1: deterministic, no LLM, declared inputs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..lib import data_point as dp
from ..lib import pointer as ptr

REPO_ROOT = Path(__file__).resolve().parents[3]
TAXONOMY_PATH = REPO_ROOT / "skills/gap_audit/references/surface-taxonomy.json"

COLLECTOR_ID = "surface_handwalk_recurrence"
KIND = "surface_handwalk"
_PROPS = {"surface": {"type": "string"}, "artifact_pointer": {"type": "object"}, "ladder_token_hits": {"type": "array", "items": {"type": "string"}}}
VALUE_SCHEMA = {"type": "object", "required": ["surface", "artifact_pointer", "ladder_token_hits"], "properties": _PROPS}
INPUTS = ["meeting-notes/*.md", "proposals/**/*.md", "skills/gap_audit/references/surface-taxonomy.json"]

_TAX = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
_SURFACES, _LADDER = _TAX["surfaces"], _TAX["ladder_tokens"]
_EXCLUDED_PREFIXES = tuple(_TAX["excluded_path_prefixes"])
_EXCLUDED_FILES = tuple(_TAX["excluded_files"])


def _walk_corpus() -> list[Path]:
    cands = sorted((REPO_ROOT / "meeting-notes").glob("*.md")) + sorted((REPO_ROOT / "proposals").rglob("*.md"))
    out: list[Path] = []
    for p in cands:
        rel = p.relative_to(REPO_ROOT).as_posix()
        if rel in _EXCLUDED_FILES or any(rel.startswith(x) for x in _EXCLUDED_PREFIXES):
            continue
        out.append(p)
    return out


def _leashed_ids() -> frozenset[str]:
    return frozenset(s["id"] for s in _SURFACES if (REPO_ROOT / "skills" / s["leash_dir"]).is_dir())


def compute_source_state() -> str:
    h = hashlib.sha256()
    h.update(b"taxonomy:" + TAXONOMY_PATH.read_bytes() + b"\0")
    h.update(b"leashed:" + ",".join(sorted(_leashed_ids())).encode() + b"\0")
    for f in _walk_corpus():
        h.update(f.relative_to(REPO_ROOT).as_posix().encode() + b"\0" + f.read_bytes() + b"\0")
    return "sha256:" + h.hexdigest()


def _ladder_hits(body: str) -> list[str]:
    return [t for t in _LADDER if t.lower() in body]


def _syn_count(body: str, syns: list[str]) -> int:
    return sum(body.count(s.lower()) for s in syns)


def collect(source_state: str) -> list[dict]:
    cp = ptr.make_unresolved(kind="collector", target={"collector_id": COLLECTOR_ID}, resolver="collector_resolver")
    leashed = _leashed_ids()
    out: list[dict] = []
    for f in _walk_corpus():
        body = f.read_text(encoding="utf-8").lower()
        lh = _ladder_hits(body)
        if len(lh) < 3:
            continue
        rel = f.relative_to(REPO_ROOT).as_posix()
        fp = ptr.make_unresolved(kind="file_path", target={"path": rel}, resolver="file_path_resolver")
        for s in _SURFACES:
            if s["id"] in leashed or _syn_count(body, s["synonyms"]) < 2:
                continue
            out.append(dp.make_data_point(
                collector_id=COLLECTOR_ID, kind=KIND,
                value={"surface": s["id"], "artifact_pointer": fp, "ladder_token_hits": lh},
                source_state=source_state, collector_pointer=cp,
            ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    rel = data_point["value"]["artifact_pointer"]["target"]["path"]
    p = REPO_ROOT / rel
    if not p.is_file():
        return "dangling", "artifact_no_longer_present"
    sid = data_point["value"]["surface"]
    if sid in _leashed_ids():
        return "dangling", "surface_now_has_a_leash"
    s = next((x for x in _SURFACES if x["id"] == sid), None)
    if s is None:
        return "dangling", "surface_no_longer_in_taxonomy"
    body = p.read_text(encoding="utf-8").lower()
    if _syn_count(body, s["synonyms"]) < 2:
        return "dangling", "surface_synonym_count_below_threshold"
    if len(_ladder_hits(body)) < 3:
        return "dangling", "ladder_vocabulary_now_below_threshold"
    return "live", "still_a_handwalk"
