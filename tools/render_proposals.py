"""Render pending proposals/ directories into one human-readable markdown.

Pure 1.0 deterministic transform — same input directory state produces
byte-identical output. Walks every proposals/{slug}/ directory, reads
proposal.json + gap.json + pre_verification.json + candidate/{name}.py,
emits a single markdown summary an operator can review without reading
raw JSON.

Not a Foundation-2 collector (emits no data points). Action program.

Usage:
  python -m tools.render_proposals          # write to proposals/REVIEW.md
  python -m tools.render_proposals --stdout # print to stdout
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROPOSALS_DIR = REPO_ROOT / "proposals"
APPROVALS_FILE = REPO_ROOT / "approvals" / "decisions.jsonl"


def _read_json(p: Path) -> dict | None:
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _load_decisions() -> dict[str, dict]:
    """Map proposal_id -> latest decision record. Last-wins on append-only file."""
    if not APPROVALS_FILE.is_file():
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


def _decision_pointer_text(rec: dict) -> str:
    """One-line transcript pointer (new shape) or legacy `by:` for the decision."""
    ab = rec.get("authorized_by")
    if isinstance(ab, dict):
        tp = ab.get("transcript_pointer") or {}
        chan = ab.get("channel", "?")
        sess = tp.get("session", "?")
        uuid = tp.get("uuid", "?")
        return f"{chan} · session `{sess}` · uuid `{uuid}`"
    by = rec.get("by")
    if isinstance(by, str):
        return f"legacy · by `{by}`"
    return "(no pointer)"


def _decision_reason_text(rec: dict) -> str | None:
    rp = rec.get("reason_pointer")
    if isinstance(rp, dict) and isinstance(rp.get("excerpt"), str):
        return rp["excerpt"]
    r = rec.get("reason")
    if isinstance(r, str):
        return r
    return None


def _verdict_emoji(v: str) -> str:
    return {"pass": "✓", "fail": "✗"}.get(v, "?")


def _render_proposal(prop_dir: Path, decisions: dict[str, dict]) -> str:
    out: list[str] = []
    manifest = _read_json(prop_dir / "proposal.json") or {}
    gap = _read_json(prop_dir / "gap.json") or {}
    prev = _read_json(prop_dir / "pre_verification.json") or {}
    pid = manifest.get("proposal_id", prop_dir.name)
    decision = decisions.get(pid)
    if decision and isinstance(decision.get("verdict"), str):
        verdict = decision["verdict"]
        status = "promoted" if verdict == "promote" else "rejected" if verdict == "reject" else manifest.get("status", "?")
    else:
        status = manifest.get("status", "?")
    cand_target = manifest.get("candidate_pointer", {}).get("target", {})
    cand_path = cand_target.get("path", "?")
    cand_id = cand_target.get("collector_id", "?")
    target_skill = "?"
    for ptr in gap.get("gap_pointers", []):
        dp_id = ptr.get("target", {}).get("data_point_id", "")
        if dp_id.startswith("skill_without_verifier:"):
            ds = REPO_ROOT / "skills" / "gap_audit" / "datasets" / "2026-04-30" / "skill_without_verifier.jsonl"
            if ds.is_file():
                for line in ds.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec.get("id") == dp_id:
                        target_skill = rec["value"]["skill_pointer"]["target"]["path"]
                        break
    out.append(f"### {pid}\n")
    out.append(f"**Target:** `{target_skill}`  &nbsp;·&nbsp;  **Status:** `{status}`  &nbsp;·&nbsp;  **Claimed kind:** `{manifest.get('claimed_kind','?')}`\n")
    if gap.get("narrative"):
        out.append(f"\n**Gap.** {gap['narrative']}\n")
    cand_full = REPO_ROOT / cand_path
    if cand_full.is_file():
        loc = sum(1 for _ in cand_full.read_text(encoding="utf-8").splitlines())
        out.append(f"\n**Candidate:** [`{cand_path}`](../{cand_path}) ({loc} lines, collector_id `{cand_id}`)\n")
    out.append("\n**Pre-verification:**\n\n")
    checks = (prev.get("value") or {}).get("checks") or {}
    if checks:
        for cid, c in checks.items():
            out.append(f"- {_verdict_emoji(c.get('verdict','?'))} `{cid}`")
            if c.get("verdict") == "fail":
                out.append(f" — {c.get('reason') or c.get('missing') or 'fail'}")
            elif "checks_passed" in c:
                out.append(f" ({c['checks_passed']}/{c.get('checks_total','?')})")
            elif "substantive_lines" in c:
                out.append(f" ({c['substantive_lines']}/{c.get('budget','?')})")
            out.append("\n")
        overall = (prev.get("value") or {}).get("overall_verdict", "?")
        out.append(f"\n**Overall:** {_verdict_emoji(overall)} `{overall}`\n")
    if decision:
        verdict = decision.get("verdict", "?")
        decided_at = decision.get("decided_at", "?")
        out.append(f"\n**Decision recorded.** Verdict `{verdict}` at `{decided_at}` — {_decision_pointer_text(decision)}\n")
        reason = _decision_reason_text(decision)
        if reason:
            out.append(f"\n> {reason}\n")
    else:
        out.append("\n**To act on this proposal:**\n\n")
        out.append("```bash\n")
        out.append("# review the candidate source:\n")
        out.append(f"cat {cand_path}\n\n")
        out.append("# promote it (writes one line to approvals/decisions.jsonl, then runs the promoter):\n")
        out.append('mkdir -p approvals\n')
        out.append(f'echo \'{{"proposal_id":"{pid}","verdict":"promote","decided_at":"<iso-now>","by":"<you>"}}\' >> approvals/decisions.jsonl\n')
        out.append(f'python -m tools.promote {pid} --dry-run   # preview\n')
        out.append(f'python -m tools.promote {pid}             # actual promote\n\n')
        out.append("# reject (just records the decision; no file move):\n")
        out.append(f'echo \'{{"proposal_id":"{pid}","verdict":"reject","decided_at":"<iso-now>","by":"<you>","reason":"<short>"}}\' >> approvals/decisions.jsonl\n')
        out.append("```\n")
    return "".join(out)


def _walk() -> list[str]:
    if not PROPOSALS_DIR.is_dir():
        return ["_No `proposals/` directory yet._\n"]
    dirs = sorted(d for d in PROPOSALS_DIR.iterdir() if d.is_dir() and (d / "proposal.json").is_file())
    if not dirs:
        return ["_No proposals on disk._\n"]
    decisions = _load_decisions()
    sections = ["# Proposals — review surface\n",
                f"\nGenerated by `tools/render_proposals.py`. {len(dirs)} proposal(s) below.\n",
                "\n---\n"]
    for d in dirs:
        sections.append("\n")
        sections.append(_render_proposal(d, decisions))
        sections.append("\n---\n")
    return sections


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    body = "".join(_walk())
    if args.stdout:
        sys.stdout.write(body)
    else:
        out = PROPOSALS_DIR / "REVIEW.md"
        out.write_text(body, encoding="utf-8")
        print(f"wrote {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
