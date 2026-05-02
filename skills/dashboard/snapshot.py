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
    bundles_dir = REPO / "skills" / "regime_audit" / "outputs"
    if not bundles_dir.is_dir():
        return []
    rows: list[dict] = []
    for run_dir in sorted(bundles_dir.glob("run-*"), key=lambda p: p.stat().st_mtime):
        stats_path = run_dir / "stats.json"
        if not stats_path.exists():
            continue
        try:
            data = json.loads(stats_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        s = data.get("stats", {})
        rows.append({
            "bundle_id": run_dir.name,
            "mtime": int(stats_path.stat().st_mtime),
            "floor_ratio": s.get("floor_ratio"),
            "by_regime": s.get("by_regime", {}),
            "by_skill": s.get("by_skill", {}),
        })
    return rows


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


def gather() -> dict:
    """Return the current snapshot as a dict. Pure read; no side effects."""
    history = _audit_history()
    latest_audit = history[-1] if history else None
    return {
        "schema_version": 2,
        "captured_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "bedrock": {p: _file_observation(p) for p in BEDROCK_FILES},
        "audit": {
            "bundle_count": len(history),
            "latest_bundle_id": latest_audit["bundle_id"] if latest_audit else None,
            "latest_floor_ratio": latest_audit["floor_ratio"] if latest_audit else None,
            "latest_by_regime": latest_audit["by_regime"] if latest_audit else {},
            "latest_by_skill": latest_audit["by_skill"] if latest_audit else {},
            "first_floor_ratio": history[0]["floor_ratio"] if history else None,
        },
        "boards": _board_observations(),
        "leashes": _leash_observations(),
        "pending_decisions": _pending_decisions(),
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
