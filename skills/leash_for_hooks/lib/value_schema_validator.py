"""value_schema_validator.py — validates collector emit against VALUE_SCHEMA.

Builds a minimal Pydantic v2 model from a collector's VALUE_SCHEMA dict and
validates each row's `value` field against it.  Keeps the projection minimal:
only checks that required fields are present; `properties` type annotations
are used when present but absent properties declarations are tolerated.

Exported surface:
    validate_collector_output(mod) -> (ok: bool, violations: list[dict])
        mod  — a collector module (has VALUE_SCHEMA, compute_source_state, collect)
        ok   — True iff every emitted row's value passes the model
        violations — list of {row_id, field_errors} for failing rows

This module does NOT call any LLM, uses no random/uuid/time-as-value, and is
deterministic given the same collector source state.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError, create_model

# Map from JSON-Schema primitive type names to Python types Pydantic understands.
_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _python_type(json_type: str) -> type:
    return _TYPE_MAP.get(json_type, Any)  # type: ignore[arg-type]


def _build_model(schema: dict) -> type[BaseModel]:
    """Derive a Pydantic model from a VALUE_SCHEMA dict.

    Only `required` and `properties` are consulted; everything else is ignored
    to keep the projection minimal (issue scope).  Required fields with no
    matching property entry default to `Any`.
    """
    required: list[str] = schema.get("required", [])
    properties: dict[str, dict] = schema.get("properties", {})

    field_defs: dict[str, Any] = {}
    for name in required:
        prop = properties.get(name, {})
        json_type = prop.get("type")
        py_type: Any = _python_type(json_type) if json_type else Any
        # Required fields: no default → Pydantic will error if absent
        field_defs[name] = (py_type, ...)

    # Optional fields declared in properties but not in required
    for name, prop in properties.items():
        if name in field_defs:
            continue
        json_type = prop.get("type")
        py_type = _python_type(json_type) if json_type else Any
        # Optional: default None
        field_defs[name] = (py_type | None, None)  # type: ignore[operator]

    return create_model("ValueModel", **field_defs)  # type: ignore[call-overload]


def validate_collector_output(mod: Any) -> tuple[bool, list[dict]]:
    """Run mod.collect() and validate each row's `value` against VALUE_SCHEMA.

    Returns (ok, violations):
        ok         — True if every row passes (including the zero-row case)
        violations — list of {row_id, field_errors} dicts for failing rows
    """
    schema: dict = getattr(mod, "VALUE_SCHEMA", {})
    model = _build_model(schema)

    source_state: str = mod.compute_source_state()
    rows: list[dict] = mod.collect(source_state)

    violations: list[dict] = []
    for row in rows:
        value = row.get("value", {})
        try:
            model.model_validate(value)
        except ValidationError as exc:
            violations.append({
                "row_id": row.get("id", "unknown"),
                "field_errors": exc.errors(include_url=False),
            })

    return (not violations), violations
