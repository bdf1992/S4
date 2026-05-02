"""Walks verifier and gap-collector sources and emits one
surface_inventory_absence data point per inline surface-scope
declaration — places where a file's "what artifacts do I cover"
knowledge is hardcoded inline rather than read from a unified
surface_inventory data-point store.

This collector measures the gap that surface_inventory (under
proposals/prop_2026-05-01_surface-inventory-and-expectation-check/)
would close. Once surface_inventory is graduated and consuming
files refactor to read from its data points, occurrences fall to
zero — that is the closure signal.

Two absence kinds detected:

  - inline_scope_constant: a top-level Assign of a name in
    {SKILL_REL, INPUTS, PY_FILES, DATASET_FILES} whose value
    names repo paths or path-globs that the file scopes itself
    to. The verifier's "what skill am I checking" or the gap
    collector's "what corpus do I walk" knowledge is inline.
  - inline_walk_function: a top-level FunctionDef named in
    {_walk, _walk_corpus, _verifier_files} that enumerates a
    directory by glob/iterdir rather than consuming a
    surface_inventory data point.

Each occurrence is one data point. verify(dp) re-parses the file
and confirms the named symbol still matches the absence kind;
files that refactor to consume surface_inventory data points
make their gap data points dangle.

This collector is itself 0.1: deterministic, no LLM, declared inputs.
Source_state hashes discovered file contents, so adding/removing/
editing any input yields a new source_state.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from ..lib import data_point as dp
from ..lib import pointer as ptr

REPO_ROOT = Path(__file__).resolve().parents[3]

COLLECTOR_ID = "surface_inventory_absence"
KIND = "surface_inventory_absence"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["absence_kind", "symbol_name", "file_pointer", "line"],
    "properties": {
        "absence_kind": {"enum": ["inline_scope_constant",
                                   "inline_walk_function"]},
        "symbol_name": {"type": "string"},
        "file_pointer": {"type": "object"},
        "line": {"type": "integer"},
    },
}
INPUTS = ["skills/*/verify.py",
          "proposals/*/candidate/*_verifier.py",
          "skills/gap_audit/collectors/*.py"]

_SCOPE_CONSTANTS = ("SKILL_REL", "INPUTS", "PY_FILES", "DATASET_FILES")
_WALK_FUNCS = ("_walk", "_walk_corpus", "_verifier_files")


def _files() -> list[Path]:
    out: list[Path] = []
    skills_root = REPO_ROOT / "skills"
    if skills_root.is_dir():
        for d in sorted(skills_root.iterdir()):
            v = d / "verify.py"
            if d.is_dir() and v.is_file():
                out.append(v)
    proposals_root = REPO_ROOT / "proposals"
    if proposals_root.is_dir():
        for prop in sorted(proposals_root.iterdir()):
            cand = prop / "candidate"
            if not cand.is_dir():
                continue
            for f in sorted(cand.iterdir()):
                if f.is_file() and f.name.endswith("_verifier.py"):
                    out.append(f)
    gc_root = REPO_ROOT / "skills/gap_audit/collectors"
    if gc_root.is_dir():
        for f in sorted(gc_root.glob("*.py")):
            if f.name not in ("__init__.py", "surface_inventory_absence.py"):
                out.append(f)
    return out


def compute_source_state() -> str:
    h = hashlib.sha256()
    for f in _files():
        rel = f.relative_to(REPO_ROOT).as_posix()
        h.update(rel.encode())
        h.update(b"\0")
        h.update(hashlib.sha256(f.read_bytes()).hexdigest().encode())
        h.update(b"\0")
    return "sha256:" + h.hexdigest()


def _scan(p: Path) -> list[tuple[str, str, int]]:
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    out: list[tuple[str, str, int]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Name)
                        and target.id in _SCOPE_CONSTANTS):
                    out.append(("inline_scope_constant",
                                target.id, node.lineno))
        elif isinstance(node, ast.FunctionDef) and node.name in _WALK_FUNCS:
            out.append(("inline_walk_function", node.name, node.lineno))
    return out


def _file_pointer(rel: str) -> dict:
    return ptr.make_unresolved(kind="file_path",
                                target={"path": rel},
                                resolver="file_path_resolver")


def collect(source_state: str) -> list[dict]:
    cp = ptr.make_unresolved(kind="collector",
                              target={"collector_id": COLLECTOR_ID},
                              resolver="collector_resolver")
    out: list[dict] = []
    for f in _files():
        rel = f.relative_to(REPO_ROOT).as_posix()
        for kind_, name, line in _scan(f):
            out.append(dp.make_data_point(
                collector_id=COLLECTOR_ID, kind=KIND,
                value={"absence_kind": kind_, "symbol_name": name,
                       "file_pointer": _file_pointer(rel),
                       "line": line},
                source_state=source_state, collector_pointer=cp,
            ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    rel = data_point["value"]["file_pointer"]["target"]["path"]
    name = data_point["value"]["symbol_name"]
    kind_ = data_point["value"]["absence_kind"]
    p = REPO_ROOT / rel
    if not p.is_file():
        return "dangling", "file_no_longer_present"
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:
        return "dangling", "syntax_error"
    for node in tree.body:
        if (kind_ == "inline_scope_constant"
                and isinstance(node, ast.Assign)):
            for target in node.targets:
                if (isinstance(target, ast.Name)
                        and target.id == name):
                    return "live", "constant_still_present"
        elif (kind_ == "inline_walk_function"
              and isinstance(node, ast.FunctionDef)
              and node.name == name):
            return "live", "function_still_present"
    return "dangling", "symbol_no_longer_present"
