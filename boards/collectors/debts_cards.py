"""Foundation 2 collector — emits one card data point per debt record.

Walks debts/D-*.json (a region of 0.3 program output: gap records the
agent or operator filed) and projects each into the baseline card-value
schema. Output accumulates as the 0.2 substrate other rungs can fence on.

See: foundations/collection-program.md, foundations/data-point.md.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from boards.lib import data_point as dp

COLLECTOR_ID = "debts_cards"
KIND = "card.debts"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["card_id", "subject", "column", "last_updated_at"],
    "properties": {
        "card_id": {"type": "string"},
        "subject": {"type": "string"},
        "column": {"type": "string"},
        "lane": {"type": ["string", "null"]},
        "last_updated_at": {"type": "string"},
        "payload": {"type": "object"},
    },
}
INPUTS = ["debts/D-*.json"]
REPO = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO / "debts"

PAYLOAD_FIELDS = (
    "kind", "principal", "interest", "payoff",
    "re_trigger", "depends_on", "closure", "supersedes", "created_at",
)


def _files() -> list[Path]:
    if not SOURCE_DIR.exists():
        return []
    return sorted(SOURCE_DIR.glob("D-*.json"))


def compute_source_state() -> str:
    h = hashlib.sha256()
    files = _files()
    for p in files:
        h.update(p.name.encode()); h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32] + ("+empty" if not files else "")


def _collector_pointer() -> dict:
    return {
        "kind": "collector", "target": {"collector_id": COLLECTOR_ID},
        "resolver": "collector_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved", "last_payload": None, "last_reason": None,
    }


def _to_card(rec: dict) -> dict | None:
    cid = rec.get("id"); sub = rec.get("subject"); col = rec.get("status")
    upd = rec.get("last_updated_at")
    if not (isinstance(cid, str) and isinstance(sub, str)
            and isinstance(col, str) and isinstance(upd, str)):
        return None
    payload = {k: rec[k] for k in PAYLOAD_FIELDS if k in rec}
    return {
        "card_id": cid, "subject": sub, "column": col,
        "lane": rec.get("severity"), "last_updated_at": upd,
        "payload": payload,
    }


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    out: list[dict] = []
    for p in _files():
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        card = _to_card(rec)
        if card is None:
            continue
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND, value=card,
            source_state=source_state, collector_pointer=cp,
        ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    cid = data_point["value"]["card_id"]
    target = SOURCE_DIR / f"{cid}.json"
    if not target.exists():
        return "dangling", "file_missing"
    try:
        rec = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "dangling", "source_unparseable"
    card = _to_card(rec)
    if card is None:
        return "dangling", "shape_changed"
    if card == data_point["value"]:
        return "live", "match"
    return "dangling", "value_drift"
