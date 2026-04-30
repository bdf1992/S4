"""Markdown corpus walker, link extractor, and target resolver.

Pure 0.1 infrastructure: walks **/*.md, tracks fenced-code-block state to
exclude links inside example fences, extracts inline-link references via
regex, and computes deterministic target receipts (live / dangling_file /
dangling_line / external / anchor_unverified) against current source.

Hoisted out of the collector to keep the collector under audit budget.
No LLM. No nondeterminism. Re-running against the same source returns
byte-identical output.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXCLUDE_DIR_PARTS = frozenset({"__pycache__", "outputs", ".git", "node_modules", ".venv"})

INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE_RE = re.compile(r"`+[^`\n]*`+")
LINE_ANCHOR_RE = re.compile(r"^L(\d+)(?:-L(\d+))?$")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "ftp://")


def walk_markdown() -> list[Path]:
    out: list[Path] = []
    for p in sorted(REPO_ROOT.rglob("*.md")):
        rel = p.relative_to(REPO_ROOT)
        if EXCLUDE_DIR_PARTS & set(rel.parts):
            continue
        out.append(p)
    return out


def hash_file_corpus(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in paths:
        rel = p.relative_to(REPO_ROOT).as_posix().encode()
        h.update(rel); h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32]


def iter_links(md_text: str) -> list[tuple[int, str, str]]:
    """Yield (line_no, link_text, href) for each inline link OUTSIDE code fences."""
    out: list[tuple[int, str, str]] = []
    in_fence = False
    for line_no, line in enumerate(md_text.splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = INLINE_CODE_RE.sub("", line)
        for m in INLINE_LINK_RE.finditer(stripped):
            out.append((line_no, m.group(1), m.group(2)))
    return out


def classify_target(href: str) -> str:
    if href.startswith(EXTERNAL_PREFIXES):
        return "external"
    if "#" not in href:
        return "repo_path"
    _, _, frag = href.partition("#")
    if LINE_ANCHOR_RE.match(frag):
        return "repo_path_line_anchored"
    return "repo_path_section_anchored"


def resolve_target(source_md: Path, href: str, target_kind: str) -> str:
    """Returns receipt: live | dangling_file | dangling_line | external | anchor_unverified."""
    if target_kind == "external":
        return "external"
    path_part, _, frag = href.partition("#")
    if not path_part:
        return "anchor_unverified"
    target = (source_md.parent / path_part).resolve()
    try:
        target.relative_to(REPO_ROOT)
    except ValueError:
        return "dangling_file"
    if not target.exists():
        return "dangling_file"
    if target_kind == "repo_path_line_anchored":
        m = LINE_ANCHOR_RE.match(frag)
        if not m or not target.is_file():
            return "dangling_line"
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        try:
            n_lines = len(target.read_text(encoding="utf-8").splitlines())
        except (UnicodeDecodeError, OSError):
            return "dangling_line"
        if start < 1 or end < start or end > n_lines:
            return "dangling_line"
        return "live"
    if target_kind == "repo_path_section_anchored":
        return "anchor_unverified"
    return "live"
