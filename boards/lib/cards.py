"""Read cards from the dataset store and project them into the shape
the markdown / html renderers expect.

The dataset is the canonical artifact (Foundation-1 data points produced
by a Foundation-2 collector). The renderers consume render-shape dicts
for ergonomics; this shim is the one-way projection.
"""
from __future__ import annotations

from pathlib import Path

from boards.lib import data_point as dp

REPO = Path(__file__).resolve().parents[2]
DATASETS = REPO / "boards" / "datasets"

# Canonical "card is awaiting work" set. Used by every meta-summary that
# counts open vs. closed across leaf boards. Drift here used to be a real
# bug — the dashboard reported 2 open factory-opportunities while the
# meta-board reported 5, because two copies disagreed on whether `mapped`
# (a gap-kind awaiting a proposal) counts as open.
OPEN_STATUSES = frozenset({"open", "pending", "proposed", "mapped"})


def dataset_path(board_name: str) -> Path:
    return DATASETS / f"{board_name}_cards.jsonl"


def has_dataset(board_name: str) -> bool:
    return dataset_path(board_name).exists()


def cards_from_dataset(board_name: str) -> list[dict]:
    """Read the board's collector output; return render-shape dicts.

    A render-shape dict mirrors the legacy card layout:
      id, subject, status, severity, last_updated_at, plus payload fields
      (payoff, principal, interest, depends_on, re_trigger, ...).
    """
    out: list[dict] = []
    for d in dp.read_jsonl(dataset_path(board_name)):
        v = d.get("value", {})
        flat = {
            "id": v.get("card_id"),
            "subject": v.get("subject"),
            "status": v.get("column"),
            "severity": v.get("lane"),
            "last_updated_at": v.get("last_updated_at"),
        }
        flat.update(v.get("payload", {}) or {})
        out.append(flat)
    return out
