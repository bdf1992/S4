"""Resolver for pointer kind `file_line`. Target shape: {path, line}.
Returns the line text on `live`, or a structured reason on `dangling`."""
from __future__ import annotations

from pathlib import Path

RESOLVER_ID = "file_line_resolver"
POINTER_KIND = "file_line"
REPO_ROOT = Path(__file__).resolve().parents[3]


def resolve(target: dict, source_state: str) -> tuple[str, object]:
    if not isinstance(target, dict) or "path" not in target or "line" not in target:
        return "dangling", "bad_target_format"
    path_str = target["path"]
    line_no = target["line"]
    if not isinstance(path_str, str) or not isinstance(line_no, int) or line_no < 1:
        return "dangling", "bad_target_types"
    p = REPO_ROOT / path_str
    if not p.exists():
        return "dangling", "path_missing"
    try:
        text = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return "dangling", "unreadable"
    lines = text.splitlines()
    if line_no > len(lines):
        return "dangling", "line_out_of_range"
    return "live", {"text": lines[line_no - 1], "path": path_str, "line": line_no}
