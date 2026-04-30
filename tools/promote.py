"""Promotion plumbing — turns operator entries in approvals/decisions.jsonl
into actual file moves from proposals/ into the live floor.

Not a Foundation-2 collector. An action program. Deterministic, no LLM,
no nondeterminism. Refuses to operate without an operator decision record.

Usage:
  python -m tools.promote <proposal_id>
  python -m tools.promote <proposal_id> --dry-run

Exit codes:
  0  promoted (or dry-run preview shown)
  1  proposal not found
  2  no operator decision record (or verdict != promote)
  3  target file already exists (refuses to overwrite)
  4  candidate file not found in proposal
  5  proposal manifest malformed
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROPOSALS_DIR = REPO_ROOT / "proposals"
APPROVALS_PATH = REPO_ROOT / "approvals" / "decisions.jsonl"


def _proposal_dir(proposal_id: str) -> Path | None:
    slug = proposal_id.replace(":", "_")
    candidate = PROPOSALS_DIR / slug
    if candidate.is_dir():
        return candidate
    for d in PROPOSALS_DIR.iterdir() if PROPOSALS_DIR.is_dir() else []:
        if d.is_dir():
            mp = d / "proposal.json"
            if mp.is_file():
                try:
                    if json.loads(mp.read_text(encoding="utf-8")).get("proposal_id") == proposal_id:
                        return d
                except json.JSONDecodeError:
                    continue
    return None


def _find_decision(proposal_id: str) -> dict | None:
    if not APPROVALS_PATH.is_file():
        return None
    for line in APPROVALS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("proposal_id") == proposal_id and rec.get("verdict") == "promote":
            return rec
    return None


def _resolve_target_skill(prop_dir: Path) -> str | None:
    gap_path = prop_dir / "gap.json"
    if not gap_path.is_file():
        return None
    gap = json.loads(gap_path.read_text(encoding="utf-8"))
    for ptr in gap.get("gap_pointers", []):
        dp_id = ptr.get("target", {}).get("data_point_id", "")
        if dp_id.startswith("skill_without_verifier:"):
            ds = REPO_ROOT / "skills" / "gap_audit" / "datasets" / "2026-04-30" / "skill_without_verifier.jsonl"
            if not ds.is_file():
                return None
            for line in ds.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("id") == dp_id:
                    return rec["value"]["skill_pointer"]["target"]["path"]
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("proposal_id")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    pd = _proposal_dir(args.proposal_id)
    if pd is None:
        print(f"proposal not found: {args.proposal_id}", file=sys.stderr); return 1
    decision = _find_decision(args.proposal_id)
    if decision is None:
        print(f"no promote decision for {args.proposal_id} in {APPROVALS_PATH}", file=sys.stderr); return 2
    target_skill_rel = _resolve_target_skill(pd)
    if target_skill_rel is None:
        print("could not resolve target skill from gap_pointers", file=sys.stderr); return 5
    cand_dir = pd / "candidate"
    py_files = sorted(p for p in cand_dir.iterdir() if p.suffix == ".py" and p.name != "__init__.py")
    if not py_files:
        print(f"no candidate .py file under {cand_dir}", file=sys.stderr); return 4
    src = py_files[0]
    dst = REPO_ROOT / target_skill_rel / "verify.py"
    if dst.exists():
        print(f"target already exists, refusing to overwrite: {dst}", file=sys.stderr); return 3
    print(f"would copy {src.relative_to(REPO_ROOT)} -> {dst.relative_to(REPO_ROOT)}")
    if args.dry_run:
        return 0
    shutil.copy2(src, dst)
    manifest = pd / "proposal.json"
    m = json.loads(manifest.read_text(encoding="utf-8"))
    m["status"] = "promoted"
    m["decision_record_pointer"] = {"kind": "data_point",
        "target": {"decision_jsonl_line_for": args.proposal_id},
        "resolver": "data_point_resolver",
        "bound_at": {"source_state": None, "resolved_at": None},
        "last_status": "unresolved", "last_payload": None, "last_reason": None}
    manifest.write_text(json.dumps(m, indent=2, sort_keys=True), encoding="utf-8")
    print(f"promoted: {target_skill_rel}/verify.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
