"""Foundation 2 collector — emits one card data point per exemplar bundle.

Walks skills/leash_*/exemplars/{proposed,promoted}/*.json. Directory name
(proposed | promoted) is the column. Filename mtime is *not* read — it is
filesystem state, not source-content state, and Foundation 2 forbids it.
last_updated_at is left null unless the bundle JSON carries a date.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from boards.lib import data_point as dp

COLLECTOR_ID = "exemplars_cards"
KIND = "card.exemplars"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["card_id", "subject", "column"],
    "properties": {
        "card_id": {"type": "string"},
        "subject": {"type": "string"},
        "column": {"type": "string"},
        "lane": {"type": ["string", "null"]},
        "last_updated_at": {"type": ["string", "null"]},
        "payload": {"type": "object"},
    },
}
INPUTS = [
    "skills/leash_*/exemplars/proposed/*.json",
    "skills/leash_*/exemplars/promoted/*.json",
]
REPO = Path(__file__).resolve().parents[2]
COLUMNS = ("proposed", "promoted")


def _files() -> list[tuple[Path, Path, str]]:
    """List (file, leash_dir, column) tuples sorted deterministically."""
    out: list[tuple[Path, Path, str]] = []
    for leash in sorted((REPO / "skills").glob("leash_*")):
        for col in COLUMNS:
            d = leash / "exemplars" / col
            if not d.is_dir():
                continue
            for p in sorted(d.glob("*.json")):
                out.append((p, leash, col))
    return out


def compute_source_state() -> str:
    h = hashlib.sha256()
    files = _files()
    for p, leash, col in files:
        rel = f"{leash.name}/{col}/{p.name}".encode()
        h.update(rel); h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32] + ("+empty" if not files else "")


def _collector_pointer() -> dict:
    return {
        "kind": "collector", "target": {"collector_id": COLLECTOR_ID},
        "resolver": "collector_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved", "last_payload": None, "last_reason": None,
    }


def _to_card(p: Path, leash: Path, col: str) -> dict | None:
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    bundle_id = raw.get("bundle_id", p.stem)
    sizes = raw.get("dataset_sizes", {})
    return {
        "card_id": f"{leash.name}/{col}/{bundle_id}",
        "subject": f"{leash.name}: {bundle_id}",
        "column": col,
        "lane": "load_bearing" if col == "promoted" else None,
        "last_updated_at": raw.get("collected_at") or raw.get("date"),
        "payload": {"leash": leash.name, "bundle_id": bundle_id, "dataset_sizes": sizes},
    }


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    out: list[dict] = []
    for p, leash, col in _files():
        c = _to_card(p, leash, col)
        if c is None:
            continue
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND, value=c,
            source_state=source_state, collector_pointer=cp,
        ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    cid = data_point["value"]["card_id"]
    for p, leash, col in _files():
        candidate = _to_card(p, leash, col)
        if candidate is not None and candidate["card_id"] == cid:
            if candidate == data_point["value"]:
                return "live", "match"
            return "dangling", "value_drift"
    return "dangling", "bundle_missing"
