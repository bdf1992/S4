"""Source-feature extraction shared by regime_audit collectors.

Pure 0.1 infrastructure: parses Python AST, reads the denylist file,
walks the repo's classifiable targets, hashes file corpora. No LLM. No
nondeterminism. The collector that consults these helpers carries the
classification rule table; this module just exposes the observable
features each rule needs.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DENYLIST_FILE = REPO_ROOT / "foundations" / "llm-sdk-denylist.txt"
EXCLUDE_DIR_PARTS = frozenset({"__pycache__", "outputs", ".git"})


def read_denylist() -> frozenset[str]:
    out: set[str] = set()
    for raw in DENYLIST_FILE.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s and not s.startswith("#"):
            out.add(s)
    return frozenset(out)


def walk_targets() -> list[Path]:
    """Returns sorted, deduplicated list of repo paths to classify."""
    targets: list[Path] = []
    skills_dir = REPO_ROOT / "skills"
    if skills_dir.exists():
        targets.extend(sorted(skills_dir.rglob("*.py")))
    targets.extend(sorted(REPO_ROOT.rglob("*.md")))
    seen: set[Path] = set()
    out: list[Path] = []
    for p in targets:
        rp = p.resolve()
        if rp in seen:
            continue
        rel = rp.relative_to(REPO_ROOT)
        if EXCLUDE_DIR_PARTS & set(rel.parts):
            continue
        seen.add(rp)
        out.append(rp)
    return out


def parse(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return None


def top_level_consts(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    out.add(tgt.id)
    return out


def import_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def call_names(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return out


def hash_file_corpus(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in paths:
        rel = p.relative_to(REPO_ROOT).as_posix().encode()
        h.update(rel)
        h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32]
