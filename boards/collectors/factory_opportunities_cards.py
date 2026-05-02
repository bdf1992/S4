"""Foundation 2 collector — emits one card data point per factory opportunity.

A factory opportunity is a stakable thing on the kit's lifecycle. Two card kinds:

  * Proposal cards. One per proposals/*/proposal.json. Column is derived from
    approvals/decisions.jsonl when a verdict is recorded; otherwise `proposed`.
  * Gap-kind cards. One per gap_audit kind whose data points are not bound by
    any proposal's gap_pointers. Column is `mapped` (pre-stake — operator
    could write a proposal binding these gaps).

Inputs (latest-per-collector for gap_audit; everything else literal):
  - skills/gap_audit/datasets/<date>/<kind>.jsonl
  - proposals/*/proposal.json
  - approvals/decisions.jsonl
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from boards.lib import data_point as dp

COLLECTOR_ID = "factory_opportunities_cards"
KIND = "card.factory_opportunities"
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
    "skills/gap_audit/datasets/<date>/<kind>.jsonl",
    "proposals/*/proposal.json",
    "approvals/decisions.jsonl",
]
COLUMNS = ["mapped", "proposed", "promoted", "rejected"]

REPO = Path(__file__).resolve().parents[2]
GAP_DATASETS_DIR = REPO / "skills" / "gap_audit" / "datasets"
PROPOSALS_DIR = REPO / "proposals"
APPROVALS_FILE = REPO / "approvals" / "decisions.jsonl"


def _latest_gap_files() -> list[Path]:
    """For each gap_audit collector kind, return the most recent dataset file."""
    if not GAP_DATASETS_DIR.exists():
        return []
    by_kind: dict[str, Path] = {}
    for date_dir in sorted(p for p in GAP_DATASETS_DIR.iterdir() if p.is_dir()):
        for f in date_dir.glob("*.jsonl"):
            by_kind[f.stem] = f
    return sorted(by_kind.values())


def _proposal_files() -> list[Path]:
    if not PROPOSALS_DIR.exists():
        return []
    return sorted(PROPOSALS_DIR.glob("*/proposal.json"))


def compute_source_state() -> str:
    h = hashlib.sha256()
    for p in _latest_gap_files():
        h.update(str(p.relative_to(REPO)).encode()); h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    for p in _proposal_files():
        h.update(str(p.relative_to(REPO)).encode()); h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    if APPROVALS_FILE.exists():
        h.update(b"approvals/decisions.jsonl\0")
        h.update(hashlib.sha256(APPROVALS_FILE.read_bytes()).digest())
    return "sha256:" + h.hexdigest()[:32]


def _collector_pointer() -> dict:
    return {
        "kind": "collector", "target": {"collector_id": COLLECTOR_ID},
        "resolver": "collector_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved", "last_payload": None, "last_reason": None,
    }


def _load_gaps() -> dict[str, dict]:
    """Map gap_data_point_id -> data_point dict (latest-per-collector inputs)."""
    out: dict[str, dict] = {}
    for p in _latest_gap_files():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict) and isinstance(rec.get("id"), str) and rec.get("kind"):
                out[rec["id"]] = rec
    return out


def _load_proposals() -> list[dict]:
    out: list[dict] = []
    for p in _proposal_files():
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            rec["_source_path"] = str(p.relative_to(REPO)).replace("\\", "/")
            out.append(rec)
    return out


def _load_decisions() -> dict[str, dict]:
    """Map proposal_id -> latest decision record (last write wins; file is append-only)."""
    if not APPROVALS_FILE.exists():
        return {}
    out: dict[str, dict] = {}
    for line in APPROVALS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        pid = rec.get("proposal_id")
        if isinstance(pid, str):
            out[pid] = rec
    return out


def _proposal_subject(proposal: dict) -> str:
    pid = proposal.get("proposal_id", "")
    parts = pid.split(":")
    if len(parts) == 3:
        return parts[2].replace("-", " ")
    return pid or "<unidentified-proposal>"


def _infer_factory_kind(pid: str) -> str:
    pid_lower = pid.lower()
    if "verifier" in pid_lower:
        return "verifier"
    if "collector" in pid_lower:
        return "collector"
    if "dashboard" in pid_lower or "board" in pid_lower or "view" in pid_lower:
        return "view"
    if "skill" in pid_lower or "audit" in pid_lower:
        return "skill"
    return "unknown"


def _decision_pointer_summary(decision: dict) -> dict | None:
    """Extract a stable transcript pointer summary across both decision schemas."""
    if isinstance(decision.get("authorized_by"), dict):
        ab = decision["authorized_by"]
        tp = ab.get("transcript_pointer")
        if isinstance(tp, dict):
            return {"channel": ab.get("channel"), "session": tp.get("session"),
                    "uuid": tp.get("uuid")}
    if isinstance(decision.get("by"), str):
        return {"channel": "legacy", "by": decision["by"]}
    return None


def _proposal_card(proposal: dict, decision: dict | None) -> dict:
    pid = proposal.get("proposal_id") or "<unidentified>"
    gap_count = len(proposal.get("gap_pointers", []) or [])
    factory_kind = _infer_factory_kind(pid)
    subject = _proposal_subject(proposal)
    manifest_status = proposal.get("status")
    install_drift = False
    if decision:
        verdict = decision.get("verdict")
        last_updated = decision.get("decided_at")
        if verdict == "reject":
            column = "rejected"
        elif verdict == "promote":
            if manifest_status == "promoted":
                column = "promoted"
            else:
                column = "proposed"
                install_drift = True
        else:
            column = "proposed"
    else:
        column = "proposed"
        last_updated = None
    if gap_count >= 5:
        lane = "load_bearing"
    elif gap_count > 0:
        lane = "cosmetic"
    else:
        lane = "unknown"
    if install_drift:
        lane = "load_bearing"
        payoff = (f"DRIFT: promote decision recorded but install never ran. "
                  f"manifest.status={manifest_status!r}; expected 'promoted'. "
                  f"run `python -m tools.promote {pid}` to consummate.")
    elif column == "proposed":
        payoff = (f"if approved: {factory_kind} gets built, addressing {gap_count} gap"
                  f"{'s' if gap_count != 1 else ''}. if rejected: gaps remain unaddressed.")
    elif column == "promoted":
        payoff = f"approved — {factory_kind} build authorized; addresses {gap_count} gap(s)."
    else:
        payoff = f"rejected — {gap_count} gap(s) released back to mapped state."
    payload: dict = {
        "factory_kind": factory_kind,
        "gap_count": gap_count,
        "source_pointer": proposal.get("_source_path", ""),
        "payoff": payoff,
    }
    if install_drift:
        payload["install_drift"] = True
        payload["manifest_status"] = manifest_status
    dp_summary = _decision_pointer_summary(decision) if decision else None
    if dp_summary:
        payload["decision_pointer"] = dp_summary
    return {
        "card_id": pid,
        "subject": subject,
        "column": column,
        "lane": lane,
        "last_updated_at": last_updated,
        "payload": payload,
    }


def _gap_kind_card(gap_kind: str, unbound_gaps: list[dict]) -> dict:
    n = len(unbound_gaps)
    if n >= 10:
        lane = "load_bearing"
    elif n >= 3:
        lane = "cosmetic"
    else:
        lane = "unknown"
    dates = [g.get("provenance", {}).get("collected_at") for g in unbound_gaps]
    dates = [d for d in dates if isinstance(d, str)]
    last_updated = max(dates) if dates else None
    payoff = (f"stake to open a factory closing {n} unaddressed {gap_kind} gap"
              f"{'s' if n != 1 else ''}. next step: write proposal binding these gaps.")
    return {
        "card_id": f"gap-kind:{gap_kind}",
        "subject": f"unaddressed {gap_kind} gaps ({n})",
        "column": "mapped",
        "lane": lane,
        "last_updated_at": last_updated,
        "payload": {
            "factory_kind": "unknown",
            "addresses_gap_kinds": [gap_kind],
            "gap_count": n,
            "source_pointer": "skills/gap_audit/datasets/",
            "payoff": payoff,
        },
    }


def collect(source_state: str) -> list[dict]:
    gaps = _load_gaps()
    proposals = _load_proposals()
    decisions = _load_decisions()

    bound_gap_ids: set[str] = set()
    for p in proposals:
        for ptr in p.get("gap_pointers", []) or []:
            if not isinstance(ptr, dict):
                continue
            gid = (ptr.get("target") or {}).get("data_point_id")
            if isinstance(gid, str):
                bound_gap_ids.add(gid)

    cp = _collector_pointer()
    out: list[dict] = []

    proposal_ids_in_files: set[str] = set()
    for p in proposals:
        pid = p.get("proposal_id")
        if not isinstance(pid, str):
            continue
        proposal_ids_in_files.add(pid)
        card = _proposal_card(p, decisions.get(pid))
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND, value=card,
            source_state=source_state, collector_pointer=cp,
        ))

    for pid, dec in decisions.items():
        if pid in proposal_ids_in_files:
            continue
        synth = {"proposal_id": pid, "_source_path": "approvals/decisions.jsonl",
                 "gap_pointers": []}
        card = _proposal_card(synth, dec)
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND, value=card,
            source_state=source_state, collector_pointer=cp,
        ))

    by_kind: dict[str, list[dict]] = {}
    for gid, g in gaps.items():
        if gid in bound_gap_ids:
            continue
        k = g.get("kind", "unknown")
        if isinstance(k, str):
            by_kind.setdefault(k, []).append(g)

    for k, glist in sorted(by_kind.items()):
        card = _gap_kind_card(k, glist)
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND, value=card,
            source_state=source_state, collector_pointer=cp,
        ))

    return out


def verify(data_point: dict) -> tuple[str, str]:
    target_id = data_point["value"]["card_id"]
    current_state = compute_source_state()
    for d in collect(current_state):
        if d["value"]["card_id"] == target_id:
            if d["value"] == data_point["value"]:
                return "live", "match"
            return "dangling", "value_drift"
    return "dangling", "card_missing"
