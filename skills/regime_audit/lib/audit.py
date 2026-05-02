"""Generic 0.1-program audit. Applied to collectors and resolvers.

Rejects programs that:
  - import any name on the LLM-SDK denylist (consulted as data points,
    NOT as raw lines from the source file — see Foundation 2),
  - directly import banned-nondeterminism modules (`random`, `time`,
    `uuid`, `socket`); `datetime` is allowed only inside lib/data_point
    (the single localized use of wall-clock for advisory `collected_at`),
  - exceed the audit budget (substantive lines of code).

`substantive_lines` excludes blank lines, lines that are pure comments,
and the module docstring. Imports count as substantive.
"""
from __future__ import annotations

import ast
from pathlib import Path

# Names banned from collectors and resolvers. Note: `datetime` is banned
# from collectors/resolvers but used inside lib/data_point.py — that file
# is the single localized exception, audited separately.
BANNED_NONDET = frozenset({"random", "uuid", "socket"})
BANNED_NONDET_TIME = frozenset({"time", "datetime"})  # extra scrutiny

DEFAULT_COLLECTOR_BUDGET = 80
DEFAULT_RESOLVER_BUDGET = 60
DEFAULT_ORCHESTRATION_BUDGET = 150


def _imports(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    return names


def _substantive_line_count(source: str) -> int:
    count = 0
    in_docstring = False
    for i, raw in enumerate(source.splitlines()):
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        if i == 0 or in_docstring:
            if s.startswith('"""') or s.startswith("'''"):
                in_docstring = not in_docstring or s.count('"""') == 2 or s.count("'''") == 2
                continue
            if in_docstring:
                continue
        count += 1
    return count


def audit_program(
    path: Path,
    *,
    llm_sdk_denylist: frozenset[str],
    budget: int,
    allow_datetime: bool = False,
) -> tuple[bool, list[str]]:
    """Returns (ok, list_of_violation_codes)."""
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return False, [f"parse_error:{exc.msg}"]
    violations: list[str] = []
    imps = _imports(tree)
    for imp in imps:
        root = imp.split(".")[0]
        full = imp
        if root in llm_sdk_denylist or full in llm_sdk_denylist:
            violations.append(f"llm_sdk_import:{full}")
        if root in BANNED_NONDET:
            violations.append(f"banned_nondet_import:{full}")
        if root in BANNED_NONDET_TIME and not allow_datetime:
            violations.append(f"banned_time_import:{full}")
    sloc = _substantive_line_count(src)
    if sloc > budget:
        violations.append(f"audit_budget_exceeded:{sloc}>{budget}")
    return (not violations), violations
