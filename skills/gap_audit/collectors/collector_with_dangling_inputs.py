"""Walks every Foundation-2 collector under skills/ and emits one
collector_with_dangling_inputs data point per declared INPUTS entry
that does not resolve at the current source state.

A collector's INPUTS list is its read-surface contract. If an entry
points at a path that no longer exists (or a glob that matches zero
files), the collector either silently emits empty output or fails
at runtime — both are floor decay.

Templated entries (containing < or >) are skipped; they are
runtime-substituted and not statically resolvable. ~ entries are
expanded via Path.expanduser before checking.

Foundation-2 conformant: deterministic, no LLM, audit budget under 80.
"""
from __future__ import annotations

import ast
import glob
import hashlib
from pathlib import Path

from ..lib import data_point as dp
from ..lib import pointer as ptr

REPO_ROOT = Path(__file__).resolve().parents[3]
COLLECTOR_ID = "collector_with_dangling_inputs"
KIND = "collector_with_dangling_inputs"
VALUE_SCHEMA = {"type": "object", "required": ["collector_pointer", "dangling_input", "kind_of_failure"]}
INPUTS = ["skills/**/collectors/*.py", "skills/**/verify.py"]
_GLOB_CHARS = set("*?[")


def _candidates() -> list[Path]:
    out: list[Path] = []
    for pat in INPUTS:
        for s in glob.glob(str(REPO_ROOT / pat), recursive=True):
            p = Path(s)
            if p.is_file() and "__pycache__" not in p.parts:
                out.append(p)
    return sorted(set(out))


def compute_source_state() -> str:
    h = hashlib.sha256()
    for p in _candidates():
        h.update(p.relative_to(REPO_ROOT).as_posix().encode()); h.update(b"\0")
        h.update(p.read_bytes()); h.update(b"\0")
    return "sha256:" + h.hexdigest()


def _extract(src: str) -> list[str] | None:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "INPUTS" for t in node.targets):
            try:
                v = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                return None
            return v if isinstance(v, list) and all(isinstance(x, str) for x in v) else None
    return []


def _check(entry: str) -> str | None:
    if "<" in entry or ">" in entry:
        return None
    has_glob = any(c in entry for c in _GLOB_CHARS)
    base = Path(entry).expanduser() if entry.startswith("~") else REPO_ROOT / entry
    if has_glob:
        return None if glob.glob(str(base), recursive=True) else "empty_glob"
    return None if base.exists() else "missing_path"


def _emit(rel: str, entry: str, failure: str, ss: str, cp: dict) -> dict:
    return dp.make_data_point(
        collector_id=COLLECTOR_ID, kind=KIND,
        value={"collector_pointer": ptr.make_unresolved(
                   kind="file_path", target={"path": rel}, resolver="file_path_resolver"),
               "dangling_input": entry, "kind_of_failure": failure},
        source_state=ss, collector_pointer=cp)


def collect(source_state: str) -> list[dict]:
    cp = ptr.make_unresolved(kind="collector", target={"collector_id": COLLECTOR_ID}, resolver="collector_resolver")
    out: list[dict] = []
    for f in _candidates():
        rel = f.relative_to(REPO_ROOT).as_posix()
        inputs = _extract(f.read_text(encoding="utf-8"))
        if inputs is None:
            out.append(_emit(rel, "<unparseable>", "unparseable_INPUTS", source_state, cp))
            continue
        for entry in inputs:
            failure = _check(entry)
            if failure:
                out.append(_emit(rel, entry, failure, source_state, cp))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    rel = data_point["value"]["collector_pointer"]["target"]["path"]
    if not (REPO_ROOT / rel).is_file():
        return "dangling", "collector_no_longer_present"
    entry = data_point["value"]["dangling_input"]
    if entry == "<unparseable>" or _check(entry):
        return "live", data_point["value"]["kind_of_failure"]
    return "dangling", "input_now_resolves"
