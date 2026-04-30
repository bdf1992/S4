"""Foundation 1 wrapper — local copy for orchestration_audit self-containment.

Mirrors boards/lib/data_point.py. Same un-grounding disclosure (Event 001) as
the original applies; debts D-001 / D-002 track the per-consumer-copy gap.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def content_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()[:16]


def make_data_point(
    *,
    collector_id: str,
    kind: str,
    value: Any,
    source_state: str,
    collector_pointer: dict,
    witness: str | None = None,
) -> dict:
    cid = content_hash(value)
    if witness is None:
        witness = cid
    return {
        "id": f"{collector_id}:{cid}",
        "kind": kind,
        "value": value,
        "provenance": {
            "collector": collector_pointer,
            "source_state": source_state,
            "collected_at": _now_iso(),
        },
        "witness": witness,
    }


def validate(dp: dict) -> tuple[bool, str]:
    if not isinstance(dp, dict):
        return False, "not_a_record"
    for field in ("id", "kind", "value", "provenance", "witness"):
        if field not in dp:
            return False, f"missing_field:{field}"
    prov = dp["provenance"]
    for sub in ("collector", "source_state", "collected_at"):
        if sub not in prov:
            return False, f"missing_field:provenance.{sub}"
    extras = set(dp.keys()) - {"id", "kind", "value", "provenance", "witness"}
    if extras:
        return False, f"extra_fields:{sorted(extras)}"
    if not isinstance(dp["id"], str) or ":" not in dp["id"]:
        return False, "bad_id_format"
    if not isinstance(dp["kind"], str) or not dp["kind"]:
        return False, "bad_kind"
    if not isinstance(prov["collector"], dict) or "kind" not in prov["collector"]:
        return False, "collector_not_pointer"
    if not isinstance(prov["source_state"], str) or not prov["source_state"]:
        return False, "bad_source_state"
    if not isinstance(dp["witness"], str) or not dp["witness"]:
        return False, "bad_witness"
    return True, "ok"


def write_jsonl(path: Path, dps: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for dp in dps:
            f.write(json.dumps(dp, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
