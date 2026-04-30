"""Validator for debt records.

Walks debts/D-*.json, applies the schema in schema.md, prints a summary,
exits 0 iff every record validates. No LLM in the loop; deterministic.

Usage:
  python -m debts.validate
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DEBTS_DIR = Path(__file__).resolve().parent

KINDS = frozenset({
    "authored_not_grounded",
    "surface_specific_bug",
    "ad_hoc_shape_no_validator",
    "missing_tool",
    "working_but_unanchored",
})
SEVERITIES = frozenset({"load_bearing", "cosmetic", "unknown"})
STATUSES = frozenset({"open", "parked", "closed_paid", "closed_written_off", "superseded"})
REQUIRED = ("id", "subject", "kind", "principal", "interest", "payoff",
            "severity", "status", "re_trigger", "created_at", "last_updated_at")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^D-\d{3,}$")


def validate(record: dict) -> list[str]:
    errs: list[str] = []
    for f in REQUIRED:
        if f not in record:
            errs.append(f"missing required field: {f}")
    if errs:
        return errs
    if not ID_RE.match(record["id"]):
        errs.append(f"id not D-NNN: {record['id']!r}")
    if record["kind"] not in KINDS:
        errs.append(f"kind not in enum: {record['kind']!r}")
    if record["severity"] not in SEVERITIES:
        errs.append(f"severity not in enum: {record['severity']!r}")
    if record["status"] not in STATUSES:
        errs.append(f"status not in enum: {record['status']!r}")
    for date_field in ("created_at", "last_updated_at"):
        if not DATE_RE.match(str(record[date_field])):
            errs.append(f"{date_field} not YYYY-MM-DD: {record[date_field]!r}")
    for prose_field in ("subject", "principal", "interest", "payoff", "re_trigger"):
        if not isinstance(record[prose_field], str) or not record[prose_field].strip():
            errs.append(f"{prose_field} must be non-empty string")
    status = record["status"]
    if status.startswith("closed_") or status == "superseded":
        if "closure" not in record:
            errs.append(f"status={status} requires 'closure' object")
        else:
            c = record["closure"]
            if not isinstance(c, dict):
                errs.append("closure must be object")
            else:
                if "evidence" not in c or not str(c.get("evidence", "")).strip():
                    errs.append("closure.evidence required and non-empty")
                if "closed_at" not in c or not DATE_RE.match(str(c.get("closed_at", ""))):
                    errs.append("closure.closed_at required, YYYY-MM-DD")
        if status == "superseded" and "supersedes" not in record:
            errs.append("status=superseded requires 'supersedes' field")
    if "depends_on" in record:
        d = record["depends_on"]
        if not isinstance(d, list) or not all(ID_RE.match(x) if isinstance(x, str) else False for x in d):
            errs.append("depends_on must be list of D-NNN ids")
    return errs


def main() -> int:
    files = sorted(DEBTS_DIR.glob("D-*.json"))
    if not files:
        print("debts: no records found")
        return 0
    seen_ids: set[str] = set()
    total_errs = 0
    for path in files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"FAIL {path.name}: json_decode: {exc}")
            total_errs += 1
            continue
        errs = validate(record)
        rid = record.get("id", "?")
        if rid in seen_ids:
            errs.append(f"duplicate id: {rid}")
        seen_ids.add(rid)
        if path.stem != rid:
            errs.append(f"filename {path.stem} does not match id {rid}")
        if errs:
            print(f"FAIL {path.name}:")
            for e in errs:
                print(f"  - {e}")
            total_errs += len(errs)
        else:
            print(f"  OK {path.name}  [{record['status']}, {record['severity']}]  {record['subject']}")
    print(f"\ndebts: {len(files)} records, {total_errs} violations")
    return 0 if total_errs == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
