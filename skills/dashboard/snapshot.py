"""Dashboard snapshot collector.

Walks live source and emits an aggregated snapshot dict. When run as main,
persists to skills/dashboard/outputs/run-<sha8>/snapshot.json.

The snapshot is a derived observation — regenerable from the same source
state, deduplicated by content hash. Persistence is what makes the delta
narrative possible. Same pattern as regime_audit's outputs/run-*/stats.json.

Usage:
  python -m skills.dashboard.snapshot          # capture and persist
  python -m skills.dashboard.snapshot --print  # capture and print to stdout
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from boards.adapters import all_boards  # noqa: E402
from boards.lib import cards as cards_lib  # noqa: E402
from skills.regime_audit.collectors import regime_classification as _ra_collect  # noqa: E402
from skills.regime_audit.lib import bundles_history as _ra_history  # noqa: E402
from skills.regime_audit.signals import regime_distribution as _ra_signal  # noqa: E402
from tools import floor_growth as _fg  # noqa: E402

OPEN_STATUSES = cards_lib.OPEN_STATUSES

BEDROCK_FILES = [
    "foundations/data-point.md",
    "foundations/collection-program.md",
    "foundations/pointer.md",
    "foundations/zero-four.md",
    "foundations/grading-events.md",
]

OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"
APPROVALS_PATH = REPO / "approvals" / "decisions.jsonl"
PROPOSALS_DIR = REPO / "proposals"


def _file_observation(rel: str) -> dict:
    p = REPO / rel
    if not p.exists():
        return {"path": rel, "exists": False}
    raw = p.read_bytes()
    return {
        "path": rel,
        "exists": True,
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "mtime_iso": _dt.date.fromtimestamp(p.stat().st_mtime).isoformat(),
    }


def _audit_history() -> list[dict]:
    return _ra_history.bundles_history()


def _audit_live() -> dict:
    """Recompute regime distribution from current source state via the signal.

    Persisted bundles in `outputs/run-*/stats.json` are observations-at-time:
    accurate when emitted, frozen thereafter. The latest persisted bundle can
    drift arbitrarily far from current source as files are added or
    reclassified. This calls the regime_audit collector + signal directly so
    the dashboard's "right now" surface tracks current state, not the most
    recent run's state. Returns the same shape as a `bundles_history()` row
    (sans `bundle_id` / `mtime`) plus `source_state` for delta diffing.
    """
    ss = _ra_collect.compute_source_state()
    rows = _ra_collect.collect(ss)
    fitted = _ra_signal.fit(rows)
    return {
        "source_state": ss,
        "total": fitted["total"],
        "floor_ratio": fitted["floor_ratio"],
        "by_regime": fitted["by_regime"],
        "by_skill": fitted["by_skill"],
    }


def _board_observations() -> dict[str, dict]:
    out: dict[str, dict] = {}
    fns = {name: fn for name, fn, _ in all_boards.SUB_BOARDS}
    for name in fns:
        cs = fns[name]()
        n_total = len(cs)
        n_open = sum(1 for c in cs if c.get("status") in OPEN_STATUSES)
        n_lb_open = sum(
            1 for c in cs
            if c.get("status") in OPEN_STATUSES and c.get("severity") == "load_bearing"
        )
        # Capture per-card identifying info for delta diffing.
        ids_open_lb = sorted(
            c.get("id", "?") for c in cs
            if c.get("status") in OPEN_STATUSES and c.get("severity") == "load_bearing"
        )
        last_dates = [c.get("last_updated_at") for c in cs if c.get("last_updated_at")]
        last_activity = max(last_dates) if last_dates else None
        out[name] = {
            "total": n_total,
            "open": n_open,
            "load_bearing_open": n_lb_open,
            "load_bearing_open_ids": ids_open_lb,
            "last_activity": last_activity,
        }
    return out


def _leash_observations() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for leash_dir in sorted(REPO.glob("skills/leash_*")):
        state_path = leash_dir / "leash_state.json"
        state = None
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8")).get("state")
            except json.JSONDecodeError:
                state = "(parse-error)"
        proposed_dir = leash_dir / "exemplars" / "proposed"
        promoted_dir = leash_dir / "exemplars" / "promoted"
        outputs_dir = leash_dir / "outputs"
        out[leash_dir.name] = {
            "state": state,
            "proposed": len(list(proposed_dir.glob("*.json"))) if proposed_dir.is_dir() else 0,
            "promoted": len(list(promoted_dir.glob("*.json"))) if promoted_dir.is_dir() else 0,
            "outputs": len(list(outputs_dir.glob("run-*"))) if outputs_dir.is_dir() else 0,
        }
    return out


def _decided_proposal_ids() -> set[str]:
    out: set[str] = set()
    if not APPROVALS_PATH.is_file():
        return out
    for line in APPROVALS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("verdict") in ("promote", "reject") and rec.get("proposal_id"):
            out.add(rec["proposal_id"])
    return out


def _resolve_target_skill(prop_dir: Path) -> str | None:
    """Walk gap_pointers -> skill_without_verifier dataset -> target skill path.

    Mirrors tools/promote.py::_resolve_target_skill so the snapshot is
    self-contained (collection program does not import action plumbing).
    """
    gap_path = prop_dir / "gap.json"
    if not gap_path.is_file():
        return None
    try:
        gap = json.loads(gap_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    for ptr in gap.get("gap_pointers", []):
        dp_id = ptr.get("target", {}).get("data_point_id", "")
        if dp_id.startswith("skill_without_verifier:"):
            ds = REPO / "skills" / "gap_audit" / "datasets" / "2026-04-30" / "skill_without_verifier.jsonl"
            if not ds.is_file():
                return None
            for line in ds.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("id") == dp_id:
                    return rec.get("value", {}).get("skill_pointer", {}).get("target", {}).get("path")
    return None


def _norm_iso(s: str) -> str:
    """Trailing 'Z' -> '+00:00' so identical UTC instants sort identically as strings."""
    return s[:-1] + "+00:00" if s.endswith("Z") else s


def _proposal_id_date(pid: str) -> str | None:
    """proposal_id 'prop:YYYY-MM-DD:slug' -> 'YYYY-MM-DDT00:00:00+00:00' (start-of-day UTC).

    The id's leading datestamp is the proposal's authoring day; we anchor its
    'appeared' event there. Returns None if the format does not match.
    """
    parts = pid.split(":", 2)
    if len(parts) < 3:
        return None
    raw = parts[1]
    if len(raw) != 10 or raw[4] != "-" or raw[7] != "-":
        return None
    return raw + "T00:00:00+00:00"


def _proposal_flow_events() -> list[dict]:
    """Time-ordered events from proposals/ + approvals/decisions.jsonl.

    Two event kinds:
      - {at, kind: 'appeared', proposal_id} — derived from proposal_id datestamp.
      - {at, kind: 'decided', proposal_id, verdict} — read from decisions.jsonl.

    Tie-break: 'appeared' before 'decided' at the same instant so a same-day
    decide-on-arrival still walks through the 'proposed' state for one boundary.
    """
    events: list[dict] = []
    if PROPOSALS_DIR.is_dir():
        for d in sorted(PROPOSALS_DIR.iterdir()):
            if not d.is_dir():
                continue
            manifest = d / "proposal.json"
            if not manifest.is_file():
                continue
            try:
                prop = json.loads(manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            pid = prop.get("proposal_id")
            if not pid:
                continue
            at = _proposal_id_date(pid)
            if not at:
                continue
            events.append({"at": at, "kind": "appeared", "proposal_id": pid})
    if APPROVALS_PATH.is_file():
        for line in APPROVALS_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            pid = rec.get("proposal_id")
            verdict = rec.get("verdict")
            at = rec.get("decided_at")
            if pid and at and verdict in ("promote", "reject"):
                events.append({
                    "at": _norm_iso(at), "kind": "decided",
                    "proposal_id": pid, "verdict": verdict,
                })
    events.sort(key=lambda e: (e["at"], 0 if e["kind"] == "appeared" else 1, e["proposal_id"]))
    return events


def _proposal_flow_series() -> list[dict]:
    """Cumulative-flow time series, one row per event boundary.

    Each row: {at, proposed, promoted, rejected, total}.
      - proposed  = currently still awaiting a decision (work-in-progress band).
      - promoted  = cumulative count of promote verdicts.
      - rejected  = cumulative count of reject verdicts.
      - total     = sum of the three (= every proposal that has ever appeared).

    Same source state -> identical series. No clock reads, no random.
    """
    events = _proposal_flow_events()
    if not events:
        return []
    state: dict[str, str] = {}
    series: list[dict] = []
    for e in events:
        pid = e["proposal_id"]
        if e["kind"] == "appeared" and pid not in state:
            state[pid] = "proposed"
        elif e["kind"] == "decided":
            v = e["verdict"]
            state[pid] = "promoted" if v == "promote" else "rejected"
        cnts = {"proposed": 0, "promoted": 0, "rejected": 0}
        for s in state.values():
            cnts[s] += 1
        series.append({
            "at": e["at"],
            "proposed": cnts["proposed"],
            "promoted": cnts["promoted"],
            "rejected": cnts["rejected"],
            "total": sum(cnts.values()),
        })
    return series


def _pending_decisions() -> list[dict]:
    if not PROPOSALS_DIR.is_dir():
        return []
    decided = _decided_proposal_ids()
    out: list[dict] = []
    for d in sorted(PROPOSALS_DIR.iterdir()):
        if not d.is_dir():
            continue
        manifest = d / "proposal.json"
        if not manifest.is_file():
            continue
        try:
            prop = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        pid = prop.get("proposal_id")
        if not pid or pid in decided:
            continue
        if prop.get("status") != "proposed":
            continue
        pre: dict = {}
        pv_path = d / "pre_verification.json"
        if pv_path.is_file():
            try:
                pv = json.loads(pv_path.read_text(encoding="utf-8"))
                v = pv.get("value", {})
                checks = v.get("checks", {})
                budget = checks.get("audit_budget_under_80", {})
                pre = {
                    "overall": v.get("overall_verdict"),
                    "audit_budget": (
                        f'{budget.get("substantive_lines", "?")}/{budget.get("budget", "?")}'
                        if budget else None
                    ),
                    "checks_total": len(checks),
                    "checks_passed": sum(1 for c in checks.values() if c.get("verdict") == "pass"),
                    "checks": checks,
                }
            except json.JSONDecodeError:
                pass
        gap_narrative = ""
        gap_path = d / "gap.json"
        if gap_path.is_file():
            try:
                gap_narrative = json.loads(gap_path.read_text(encoding="utf-8")).get("narrative", "")
            except json.JSONDecodeError:
                pass
        candidate_path = (
            prop.get("candidate_pointer", {}).get("target", {}).get("path") or ""
        )
        candidate_lines = None
        if candidate_path:
            cp = REPO / candidate_path
            if cp.is_file():
                candidate_lines = sum(1 for _ in cp.read_text(encoding="utf-8").splitlines())
        target_skill = _resolve_target_skill(d)
        target_verify_path = f"{target_skill}/verify.py" if target_skill else None
        target_exists = bool(target_verify_path and (REPO / target_verify_path).is_file())
        out.append({
            "proposal_id": pid,
            "claimed_kind": prop.get("claimed_kind"),
            "target_skill_path": target_skill,
            "target_verify_path": target_verify_path,
            "target_exists": target_exists,
            "candidate_path": candidate_path,
            "candidate_lines": candidate_lines,
            "gap_narrative": gap_narrative,
            "pre_verification": pre,
            "stakes": prop.get("stakes"),
            "proposal_dir": d.relative_to(REPO).as_posix(),
        })
    return out


def _floor_growth_observation() -> dict:
    """Per-skill peer-consumption status + ranked next-target candidates.

    Calls tools.floor_growth.collect() — same data the operator sees from
    `python -m tools.floor_growth --ranked` and at the top of `/cook`. The
    ranking buckets are computed by walking _fg.LEVERAGE_RULES against the
    collected per-skill values, so the dashboard surfaces the same leverage
    judgement floor_growth itself emits.
    """
    source_state = _fg.compute_source_state()
    points = _fg.collect(source_state)
    by_skill: dict[str, dict] = {}
    counts = {"graduated": 0, "candidate": 0, "isolated": 0, "no_structure": 0}
    for p in points:
        v = p["value"]
        name = v["skill_name"]
        importers = v["peer_importers"]
        by_skill[name] = {
            "status": v["status"],
            "verifier_present": v["verifier_present"],
            "lib_consumed": v["lib_consumed"],
            "signals_consumed": v["signals_consumed"],
            "collectors_consumed": v["collectors_consumed"],
            "importer_count": len(importers),
            "importers": importers,
        }
        if v["status"] in counts:
            counts[v["status"]] += 1
    ranked: list[dict] = []
    used: set[str] = set()
    for rule_id, rule_text, pred in _fg.LEVERAGE_RULES:
        bucket: list[str] = []
        for p in points:
            v = p["value"]
            if v["skill_name"] in used:
                continue
            if pred(v):
                bucket.append(v["skill_name"])
                used.add(v["skill_name"])
        if bucket:
            ranked.append({
                "rule_id": rule_id,
                "rule_text": rule_text,
                "skills": sorted(bucket),
            })
    return {
        "source_state": source_state,
        "by_skill": by_skill,
        "counts": counts,
        "ranked": ranked,
    }


def _claim_health_observation() -> dict:
    """Walk every markdown file via the sibling skill and surface its
    `claim_health` signal. First peer importer of `skills.claim_audit`
    (top of the `isolated_with_signals` bucket per
    `tools.floor_growth.LEVERAGE_RULES`) — every other dashboard section
    renders prose pointing at source via markdown links, and a renderer
    that ships dangling pointers is the surface contradicting itself."""
    from skills.claim_audit.collectors import markdown_claims
    from skills.claim_audit.signals import claim_health

    rows = markdown_claims.collect(markdown_claims.compute_source_state())
    fitted = claim_health.fit(rows)
    if fitted["total"] == 0:
        verdict = "no_data"
    else:
        lr = fitted.get("live_ratio")
        verdict = ("healthy" if (lr is None or lr >= claim_health.DEGRADED_THRESHOLD)
                   else "degraded")

    dangling: list[dict] = []
    for r in rows:
        v = r.get("value", {})
        if v.get("receipt") in ("dangling_file", "dangling_line"):
            dangling.append({
                "source": v["source"], "line": v["line"],
                "target_raw": v["target_raw"], "receipt": v["receipt"],
            })
    dangling.sort(key=lambda d: (d["source"], d["line"]))

    by_source = fitted.get("by_source", {})
    sources_dangling: list[dict] = []
    for src, cnts in by_source.items():
        n = cnts.get("dangling_file", 0) + cnts.get("dangling_line", 0)
        if n:
            sources_dangling.append({"source": src, "count": n})
    sources_dangling.sort(key=lambda d: (-d["count"], d["source"]))

    return {
        "verdict": verdict,
        "total": fitted["total"],
        "internal": fitted["internal"],
        "live": fitted["live"],
        "dangling": fitted["dangling"],
        "unverified_anchor": fitted["unverified_anchor"],
        "live_ratio": fitted["live_ratio"],
        "degraded_threshold": claim_health.DEGRADED_THRESHOLD,
        "top_dangling_sources": sources_dangling[:10],
        "dangling_links": dangling[:50],
    }


def gather() -> dict:
    """Return the current snapshot as a dict. Pure read; no side effects."""
    history = _audit_history()
    latest_audit = history[-1] if history else None
    live_audit = _audit_live()
    return {
        "schema_version": 5,
        "captured_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "bedrock": {p: _file_observation(p) for p in BEDROCK_FILES},
        "audit": {
            "bundle_count": len(history),
            "latest_bundle_id": latest_audit["bundle_id"] if latest_audit else None,
            "latest_floor_ratio": latest_audit["floor_ratio"] if latest_audit else None,
            "latest_by_regime": latest_audit["by_regime"] if latest_audit else {},
            "latest_by_skill": latest_audit["by_skill"] if latest_audit else {},
            "first_floor_ratio": history[0]["floor_ratio"] if history else None,
            "live_floor_ratio": live_audit["floor_ratio"],
            "live_by_regime": live_audit["by_regime"],
            "live_by_skill": live_audit["by_skill"],
            "live_total": live_audit["total"],
            "live_source_state": live_audit["source_state"],
        },
        "boards": _board_observations(),
        "leashes": _leash_observations(),
        "floor_growth": _floor_growth_observation(),
        "claim_health": _claim_health_observation(),
        "pending_decisions": _pending_decisions(),
        "proposal_flow": _proposal_flow_series(),
    }


def _content_hash(snap: dict) -> str:
    # Hash everything except the wall-clock timestamp so identical state
    # collapses to the same bundle id.
    copy = {k: v for k, v in snap.items() if k != "captured_at"}
    blob = json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def persist(snap: dict) -> Path:
    """Write snapshot to outputs/run-<sha8>/snapshot.json. Returns the path.

    If a bundle with the same content hash already exists, returns its path
    without overwriting (idempotent).
    """
    bundle_id = f"run-{_content_hash(snap)}"
    bundle_dir = OUTPUTS_DIR / bundle_id
    bundle_dir.mkdir(parents=True, exist_ok=True)
    out_path = bundle_dir / "snapshot.json"
    if not out_path.exists():
        out_path.write_text(
            json.dumps(snap, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return out_path


def find_latest_persisted() -> dict | None:
    """Return the most recent persisted snapshot dict, or None."""
    if not OUTPUTS_DIR.is_dir():
        return None
    runs = sorted(OUTPUTS_DIR.glob("run-*/snapshot.json"), key=lambda p: p.stat().st_mtime)
    if not runs:
        return None
    try:
        return json.loads(runs[-1].read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def main() -> int:
    args = sys.argv[1:]
    snap = gather()
    if "--print" in args:
        print(json.dumps(snap, indent=2, sort_keys=True))
        return 0
    path = persist(snap)
    rel = path.relative_to(REPO).as_posix()
    print(f"snapshot persisted: {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
