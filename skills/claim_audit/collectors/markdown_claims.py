"""Walks **/*.md and emits one md_link data point per inline markdown link.

Each data point carries a deterministic receipt — live, dangling_file,
dangling_line, external, or anchor_unverified — computed against current
source state by `lib.markdown_walk.resolve_target`. Classification is
procedural (regex + path resolution + line-count check); fuzzy cases
(section anchors) are emitted as `anchor_unverified` rather than guessed.

Punts (v1, documented as kind boundaries — not mechanically extractable
without LLM judgment):
  - reference-style links `[text][ref]` and `[ref]: url` definitions,
  - autolinks `<https://example.com>`,
  - bare paths in prose ("see foundations/data-point.md"),
  - natural-language assertions ("Move 1 done", "harness produces siblings").
"""
from __future__ import annotations

from pathlib import Path

from ..lib import data_point as dp
from ..lib import markdown_walk as mw

COLLECTOR_ID = "markdown_claims"
KIND = "md_link"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["source", "line", "target_raw", "target_kind", "receipt"],
}
INPUTS = ["**/*.md"]
REPO_ROOT = mw.REPO_ROOT


def compute_source_state() -> str:
    return mw.hash_file_corpus(mw.walk_markdown())


def _collector_pointer() -> dict:
    return {"kind": "collector", "target": {"collector_id": COLLECTOR_ID},
            "resolver": "collector_resolver",
            "bound_at": {"source_state": None, "resolved_at": None},
            "last_status": "unresolved", "last_payload": None, "last_reason": None}


def collect(source_state: str) -> list[dict]:
    cp = _collector_pointer()
    out: list[dict] = []
    for md in mw.walk_markdown():
        rel = md.relative_to(REPO_ROOT).as_posix()
        try:
            text = md.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, _txt, href in mw.iter_links(text):
            target_kind = mw.classify_target(href)
            receipt = mw.resolve_target(md, href, target_kind)
            out.append(dp.make_data_point(
                collector_id=COLLECTOR_ID, kind=KIND,
                value={"source": rel, "line": line_no, "target_raw": href,
                       "target_kind": target_kind, "receipt": receipt},
                source_state=source_state, collector_pointer=cp,
            ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    rel = data_point["value"]["source"]
    if not (REPO_ROOT / rel).exists():
        return "dangling", "source_missing"
    return "live", data_point["value"]["receipt"]
