"""Foundation 2 meta-collector — kanban of kanbans.

Reads the leaf card datasets (boards/datasets/<name>_cards.jsonl) and
emits one card per sub-board. Each meta-card carries computed health
summary in its value: total / open / load-bearing-open counts, last
activity date, status column (needs_attention | healthy).

Source is the leaf datasets, not the underlying repo source. Inputs are
boards/datasets/*_cards.jsonl. source_state is hashed over those files.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from boards.lib import cards as cards_lib
from boards.lib import data_point as dp

COLLECTOR_ID = "all_cards"
KIND = "card.all"
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
REPO = Path(__file__).resolve().parents[2]
DATASETS = REPO / "boards" / "datasets"

LEAF_BOARDS = ("debts", "grading-events", "exemplars", "factory-opportunities")
OPEN_STATUSES = cards_lib.OPEN_STATUSES

INPUTS = [f"boards/datasets/{n}_cards.jsonl" for n in LEAF_BOARDS]


def _leaf_path(name: str) -> Path:
    return DATASETS / f"{name}_cards.jsonl"


def compute_source_state() -> str:
    h = hashlib.sha256()
    any_present = False
    for name in LEAF_BOARDS:
        p = _leaf_path(name)
        h.update(name.encode()); h.update(b"\0")
        if p.exists():
            any_present = True
            h.update(hashlib.sha256(p.read_bytes()).digest())
        else:
            h.update(b"missing")
    return "sha256:" + h.hexdigest()[:32] + ("" if any_present else "+empty")


def _collector_pointer() -> dict:
    return {
        "kind": "collector", "target": {"collector_id": COLLECTOR_ID},
        "resolver": "collector_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved", "last_payload": None, "last_reason": None,
    }


def _summarize(name: str) -> dict:
    p = _leaf_path(name)
    cards = [d.get("value", {}) for d in dp.read_jsonl(p)]
    total = len(cards)
    n_open = sum(1 for v in cards if v.get("column") in OPEN_STATUSES)
    n_lb_open = sum(
        1 for v in cards
        if v.get("column") in OPEN_STATUSES and v.get("lane") == "load_bearing"
    )
    dates = [v.get("last_updated_at") for v in cards if v.get("last_updated_at")]
    last_activity = max(dates) if dates else None
    column = "needs_attention" if n_lb_open > 0 else "healthy"
    subject = (f"{total} cards · {n_open} open · "
               f"{n_lb_open} load-bearing-open · last: {last_activity or '-'}")
    return {
        "card_id": name,
        "subject": subject,
        "column": column,
        "lane": "load_bearing" if column == "needs_attention" else "cosmetic",
        "last_updated_at": last_activity,
        "payload": {
            "total": total, "open": n_open, "load_bearing_open": n_lb_open,
            "dataset_present": p.exists(),
            "leaf_dataset": str(p.relative_to(REPO)).replace("\\", "/"),
        },
    }


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    return [
        dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND, value=_summarize(n),
            source_state=source_state, collector_pointer=cp,
        )
        for n in LEAF_BOARDS
    ]


def verify(data_point: dict) -> tuple[str, str]:
    name = data_point["value"]["card_id"]
    if name not in LEAF_BOARDS:
        return "dangling", "unknown_leaf"
    fresh = _summarize(name)
    if fresh == data_point["value"]:
        return "live", "match"
    return "dangling", "value_drift"
