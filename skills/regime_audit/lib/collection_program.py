"""Foundation 2 — collector validator.

Walks a candidate collector module path; verifies it declares the required
top-level constants/entry points and passes the generic 0.1-program audit
from `lib.audit`. Returns (ok, list_of_violation_codes).
"""
from __future__ import annotations

import ast
from pathlib import Path

from . import audit

REQUIRED_CONSTANTS = ("COLLECTOR_ID", "KIND", "VALUE_SCHEMA", "INPUTS")
REQUIRED_FUNCTIONS = ("collect", "verify")


def _top_level_names(tree: ast.AST) -> tuple[set[str], set[str]]:
    consts: set[str] = set()
    funcs: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    consts.add(tgt.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.add(node.name)
    return consts, funcs


def validate_collector(
    path: Path,
    *,
    llm_sdk_denylist: frozenset[str],
    budget: int = audit.DEFAULT_COLLECTOR_BUDGET,
) -> tuple[bool, list[str]]:
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return False, [f"parse_error:{exc.msg}"]
    consts, funcs = _top_level_names(tree)
    violations: list[str] = []
    for c in REQUIRED_CONSTANTS:
        if c not in consts:
            violations.append(f"missing_constant:{c}")
    for f in REQUIRED_FUNCTIONS:
        if f not in funcs:
            violations.append(f"missing_function:{f}")
    ok, audit_v = audit.audit_program(
        path,
        llm_sdk_denylist=llm_sdk_denylist,
        budget=budget,
        allow_datetime=False,
    )
    violations.extend(audit_v)
    return (not violations), violations


def validate_resolver(
    path: Path,
    *,
    llm_sdk_denylist: frozenset[str],
    budget: int = audit.DEFAULT_RESOLVER_BUDGET,
) -> tuple[bool, list[str]]:
    """Resolvers share Foundation 2's audit constraints but expose
    `resolve(target, source_state) -> (status, payload_or_reason)` as their
    entry point instead of collect/verify."""
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return False, [f"parse_error:{exc.msg}"]
    consts, funcs = _top_level_names(tree)
    violations: list[str] = []
    if "RESOLVER_ID" not in consts:
        violations.append("missing_constant:RESOLVER_ID")
    if "POINTER_KIND" not in consts:
        violations.append("missing_constant:POINTER_KIND")
    if "resolve" not in funcs:
        violations.append("missing_function:resolve")
    ok, audit_v = audit.audit_program(
        path,
        llm_sdk_denylist=llm_sdk_denylist,
        budget=budget,
        allow_datetime=False,
    )
    violations.extend(audit_v)
    return (not violations), violations
