"""Walks verifier sources (skills/*/verify.py and
proposals/*/candidate/*_verifier.py) and emits one verifier_redundancy
data point per (symbol_name, structural_hash) that occurs in two or
more files.

Two redundancy kinds are detected:

  - function: top-level FunctionDef whose *body* (ignoring signature
    and decorators) ast-dumps to identical text. Signature-only
    differences are not counted; structural body identity is.
  - constant: top-level Assign of the form NAME = <literal>, where
    the literal is a tuple/list/set of strings or a bare string.
    Identity is on (name, JSON-canonical literal value).

Every duplicated helper or denylist constant across verifier
candidates is one redundancy data point. Promoting a parameterized
bundle_verifier collapses these into a single library, and the
collector's output goes to zero, which is the closure signal.

This collector is itself 0.1: deterministic, no LLM, declared inputs.
Its source_state hashes the discovered verifier file contents, so
adding/removing/editing any verifier yields a new source_state.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from ..lib import data_point as dp
from ..lib import pointer as ptr

REPO_ROOT = Path(__file__).resolve().parents[3]

COLLECTOR_ID = "verifier_redundancy"
KIND = "verifier_redundancy"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["redundancy_kind", "symbol_name", "body_hash", "occurrences"],
    "properties": {
        "redundancy_kind": {"enum": ["function", "constant"]},
        "symbol_name": {"type": "string"},
        "body_hash": {"type": "string"},
        "occurrences": {"type": "array", "minItems": 2,
                        "items": {"type": "object",
                                  "required": ["file", "line"]}},
    },
}
INPUTS = ["skills/*/verify.py", "proposals/*/candidate/*_verifier.py"]


def _verifier_files() -> list[Path]:
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
    return out


def compute_source_state() -> str:
    h = hashlib.sha256()
    for f in _verifier_files():
        rel = f.relative_to(REPO_ROOT).as_posix()
        h.update(rel.encode())
        h.update(b"\0")
        h.update(hashlib.sha256(f.read_bytes()).hexdigest().encode())
        h.update(b"\0")
    return "sha256:" + h.hexdigest()


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        return body[1:]
    return body


def _function_signature(symbols: dict, file_rel: str, node: ast.FunctionDef) -> None:
    body = _strip_docstring(node.body)
    canonical = "[" + ",".join(ast.dump(s, annotate_fields=True,
                                        include_attributes=False) for s in body) + "]"
    bh = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()[:16]
    key = ("function", node.name, bh)
    symbols.setdefault(key, []).append((file_rel, node.lineno))


def _constant_signature(symbols: dict, file_rel: str, node: ast.Assign) -> None:
    if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
        return
    name = node.targets[0].id
    try:
        value = ast.literal_eval(node.value)
    except (ValueError, SyntaxError):
        return
    if not isinstance(value, (str, tuple, list, set, frozenset)):
        return
    if isinstance(value, (set, frozenset)):
        value = sorted(value)
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"),
                           default=list)
    bh = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()[:16]
    key = ("constant", name, bh)
    symbols.setdefault(key, []).append((file_rel, node.lineno))


def _scan(file_path: Path) -> tuple[str, ast.Module] | None:
    rel = file_path.relative_to(REPO_ROOT).as_posix()
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None
    return rel, tree


def _collector_pointer() -> dict:
    return ptr.make_unresolved(
        kind="collector",
        target={"collector_id": COLLECTOR_ID},
        resolver="collector_resolver",
    )


def _file_pointer(rel: str) -> dict:
    return ptr.make_unresolved(
        kind="file_path",
        target={"path": rel},
        resolver="file_path_resolver",
    )


def collect(source_state: str) -> list[dict]:
    symbols: dict[tuple[str, str, str], list[tuple[str, int]]] = {}
    for f in _verifier_files():
        scanned = _scan(f)
        if scanned is None:
            continue
        rel, tree = scanned
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                _function_signature(symbols, rel, node)
            elif isinstance(node, ast.Assign):
                _constant_signature(symbols, rel, node)

    cp = _collector_pointer()
    out: list[dict] = []
    for (kind_, name, bh), occs in sorted(symbols.items()):
        if len(occs) < 2:
            continue
        occurrences = [
            {"file": _file_pointer(rel), "line": line}
            for rel, line in sorted(occs)
        ]
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND,
            value={
                "redundancy_kind": kind_,
                "symbol_name": name,
                "body_hash": bh,
                "occurrences": occurrences,
            },
            source_state=source_state, collector_pointer=cp,
        ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    occs = data_point["value"]["occurrences"]
    present = 0
    for occ in occs:
        rel = occ["file"]["target"]["path"]
        if (REPO_ROOT / rel).is_file():
            present += 1
    if present < 2:
        return "dangling", f"only_{present}_files_remain"
    return "live", f"{present}_of_{len(occs)}_files_present"
