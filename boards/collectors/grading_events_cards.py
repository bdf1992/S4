"""Foundation 2 collector — emits one card data point per grading event.

Walks foundations/grading-events.md and parses H2 sections of the form
    ## Event NNN — <subject> (<STATUS>[ <YYYY-MM-DD>])

Source is a single markdown file; source_state is its content hash.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from boards.lib import data_point as dp

COLLECTOR_ID = "grading_events_cards"
KIND = "card.grading_events"
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
INPUTS = ["foundations/grading-events.md"]
REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "foundations" / "grading-events.md"

H2_PATTERN = re.compile(
    r"^##\s+Event\s+(\d+)\s+—\s+(.+?)\s+\(([A-Z]+)(?:\s+(\d{4}-\d{2}-\d{2}))?\)\s*$"
)


def compute_source_state() -> str:
    if not SOURCE.exists():
        return "sha256:" + ("0" * 32) + "+missing"
    h = hashlib.sha256()
    h.update(SOURCE.read_bytes())
    return "sha256:" + h.hexdigest()[:32]


def _collector_pointer() -> dict:
    return {
        "kind": "collector", "target": {"collector_id": COLLECTOR_ID},
        "resolver": "collector_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved", "last_payload": None, "last_reason": None,
    }


def _events() -> list[dict]:
    if not SOURCE.exists():
        return []
    out: list[dict] = []
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        m = H2_PATTERN.match(line)
        if not m:
            continue
        num, subject, status, date = m.group(1), m.group(2), m.group(3), m.group(4)
        out.append({
            "card_id": f"E-{int(num):03d}",
            "subject": subject.strip(),
            "column": status.lower(),
            "lane": None,
            "last_updated_at": date,
            "payload": {"event_number": int(num), "raw_status": status},
        })
    return out


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    return [
        dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND, value=ev,
            source_state=source_state, collector_pointer=cp,
        )
        for ev in _events()
    ]


def verify(data_point: dict) -> tuple[str, str]:
    target_id = data_point["value"]["card_id"]
    for ev in _events():
        if ev["card_id"] == target_id:
            if ev == data_point["value"]:
                return "live", "match"
            return "dangling", "value_drift"
    return "dangling", "event_missing"
