"""Generic 0.1-program audit. Applied to collectors and resolvers.

Rejects programs that:
  - import any name on the LLM-SDK denylist (consulted as data points,
    NOT as raw lines from the source file — see Foundation 2),
  - directly import banned-nondeterminism modules (`random`, `time`,
    `uuid`, `socket`); `datetime` is allowed only inside lib/data_point
    (the single localized use of wall-clock for advisory `prov:wasGeneratedAtTime`),
  - exceed the audit budget (cyclomatic complexity per McCabe 1976,
    NIST SP 500-235; computed via radon's cc_visit, defaults of <= 10
    per function and <= 30 cumulative per module — see
    https://radon.readthedocs.io/).
"""
from __future__ import annotations

import ast
from pathlib import Path

from radon.complexity import cc_visit

# Names banned from collectors and resolvers. Note: `datetime` is banned
# from collectors/resolvers but used inside lib/data_point.py — that file
# is the single localized exception, audited separately.
BANNED_NONDET = frozenset({"random", "uuid", "socket"})
BANNED_NONDET_TIME = frozenset({"time", "datetime"})  # extra scrutiny

DEFAULT_PER_FUNCTION = 10
DEFAULT_COLLECTOR_BUDGET = 30
DEFAULT_RESOLVER_BUDGET = 30
DEFAULT_ORCHESTRATION_BUDGET = 30


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


def _complexity_violations(src: str, *, budget: int, per_function: int) -> list[str]:
    violations: list[str] = []
    cumulative = 0
    for b in cc_visit(src):
        cumulative += b.complexity
        if b.complexity > per_function:
            violations.append(
                f"function_complexity_exceeded:{b.name}:{b.complexity}>{per_function}")
    if cumulative > budget:
        violations.append(f"module_complexity_exceeded:{cumulative}>{budget}")
    return violations


def audit_program(
    path: Path,
    *,
    llm_sdk_denylist: frozenset[str],
    budget: int,
    allow_datetime: bool = False,
    per_function: int = DEFAULT_PER_FUNCTION,
) -> tuple[bool, list[str]]:
    """Returns (ok, list_of_violation_codes).

    `budget` is the maximum cumulative cyclomatic complexity for the module
    (formerly: substantive lines of code). `per_function` caps any single
    function's cyclomatic complexity.
    """
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
    violations += _complexity_violations(src, budget=budget, per_function=per_function)
    return (not violations), violations
