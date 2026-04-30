"""HTML render of pending proposals/ — provenance-explicit, validator
explanations in plain language, candidate source preview, action commands.

Pure 0.1 deterministic transform. Self-contained HTML (inline CSS, no
external assets). Shows the full chain of trust: gap-collector ->
gap data point -> proposal -> pre-verification -> awaits operator.

Usage:
  python -m tools.render_proposals_html
  python -m tools.render_proposals_html --stdout
"""
from __future__ import annotations

import argparse
import html as _html
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROPOSALS_DIR = REPO_ROOT / "proposals"
DATASETS_DIR = REPO_ROOT / "skills" / "gap_audit" / "datasets" / "2026-04-30"

CHECK_GLOSSARY = {
    "required_constants_present": (
        "Top-level COLLECTOR_ID, KIND, VALUE_SCHEMA, INPUTS declared",
        "Foundation 2 requires these as constants. Without them the candidate is not a recognizable collector — its kind, output schema, and read-surface are undeclared."),
    "required_functions_present": (
        "collect() and verify() entry points exist",
        "Foundation 2's two-function interface. collect() emits data points; verify() re-walks them. Without both, the collector cannot be re-run or self-checked."),
    "no_llm_sdk_imports": (
        "No anthropic / openai / google.generativeai / cohere imports",
        "Bedrock rule: a 0.1 collector cannot depend on a language model. If it did, the bottom of the ladder would be a model output — circular grading."),
    "no_nondeterminism_imports": (
        "No random / uuid / secrets imports",
        "Same source state must produce byte-identical output. datetime is allowed only inside provenance.collected_at, which Foundation 1 designates advisory and not load-bearing."),
    "audit_budget_under_80": (
        "Substantive lines ≤ 80",
        "Foundation 2's smallness rule. A small program's diff is loud; a large program's diff is camouflage. Reviewed in one sitting."),
    "determinism_runtime_check": (
        "Two collect() runs produced byte-identical witnesses",
        "Live confirmation that determinism holds — not just structurally absent banned imports, but actually deterministic in execution."),
    "candidate_runs_clean_against_target": (
        "Running the candidate against the live target skill — every check passed",
        "End-to-end smoke test. The candidate is invoked against its declared INPUTS and every emitted bundle_self_check has verdict=pass."),
}

CSS = """
* { box-sizing: border-box; }
body { font: 14px/1.5 -apple-system, system-ui, "Segoe UI", sans-serif; max-width: 1100px; margin: 2em auto; padding: 0 1em; color: #1a1a1a; background: #fafaf8; }
h1, h2, h3 { color: #2a2a2a; }
h1 { border-bottom: 2px solid #2a2a2a; padding-bottom: .3em; }
.intro { background: #f0eee8; padding: 1em 1.5em; border-radius: 6px; border-left: 4px solid #555; }
.intro p { margin: .5em 0; }
.proposal { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 1.5em; margin: 2em 0; box-shadow: 0 1px 3px rgba(0,0,0,.05); }
.proposal-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: .5em; }
.proposal-header h2 { margin: 0; font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 1em; }
.badge { display: inline-block; padding: .15em .6em; border-radius: 999px; font-size: .85em; font-weight: 600; }
.badge.pass { background: #d4edda; color: #155724; }
.badge.fail { background: #f8d7da; color: #721c24; }
.badge.proposed { background: #e7f0fa; color: #1d4f8a; }
.badge.promoted { background: #c3e6cb; color: #155724; }
.badge.rejected { background: #f5c6cb; color: #721c24; }
.kv { display: grid; grid-template-columns: max-content 1fr; gap: .25em 1em; margin: 1em 0; }
.kv dt { font-weight: 600; color: #555; }
.kv dd { margin: 0; font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: .9em; }
.provenance { display: flex; align-items: stretch; gap: .5em; margin: 1.5em 0; overflow-x: auto; }
.prov-step { background: #f6f4ee; border: 1px solid #d8d4ca; border-radius: 6px; padding: .75em 1em; min-width: 180px; flex: 1; }
.prov-step strong { display: block; color: #444; font-size: .8em; text-transform: uppercase; letter-spacing: .5px; margin-bottom: .35em; }
.prov-step code { font-size: .8em; word-break: break-all; }
.prov-arrow { display: flex; align-items: center; color: #888; font-size: 1.5em; }
.gap-narrative { background: #fff8e8; border-left: 4px solid #d4a000; padding: .75em 1em; margin: 1em 0; border-radius: 0 4px 4px 0; }
table.checks { width: 100%; border-collapse: collapse; margin: 1em 0; }
table.checks th, table.checks td { padding: .6em .75em; text-align: left; vertical-align: top; border-bottom: 1px solid #eee; }
table.checks th { background: #f6f4ee; font-weight: 600; font-size: .85em; text-transform: uppercase; letter-spacing: .5px; color: #555; }
table.checks code { background: #f0eee8; padding: 1px 5px; border-radius: 3px; font-size: .85em; }
table.checks .why { color: #666; font-size: .9em; }
table.checks .res { white-space: nowrap; }
.preview { background: #2a2a2a; color: #d4d4d4; padding: 1em; border-radius: 4px; overflow-x: auto; font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: .85em; line-height: 1.45; }
details { margin: 1em 0; padding: .5em 1em; background: #f6f4ee; border-radius: 4px; }
details summary { cursor: pointer; font-weight: 600; }
details pre { background: #2a2a2a; color: #d4d4d4; padding: 1em; border-radius: 4px; margin: .75em 0; overflow-x: auto; font-size: .85em; }
.metric { display: inline-block; padding: 1px 8px; background: #e7f0fa; border-radius: 3px; font-family: ui-monospace, monospace; font-size: .85em; color: #1d4f8a; }
.no-data { color: #999; font-style: italic; }
.summary { background: linear-gradient(135deg, #f0f4ee 0%, #e8efe2 100%); padding: 1.25em 1.5em; border-radius: 8px; border-left: 4px solid #2d7a3e; margin: 1em 0 2em; }
.summary h2 { margin: 0 0 .5em; color: #1a4a26; }
.chips { display: flex; flex-wrap: wrap; gap: .5em; margin: .75em 0 1em; }
.chip { background: #fff; border: 1px solid #cfd8c8; padding: .35em .8em; border-radius: 999px; font-size: .9em; }
.chip strong { color: #2d7a3e; }
.chip.proposed { background: #e7f0fa; border-color: #b9d2ee; }
.chip.proposed strong { color: #1d4f8a; }
.chip.promoted { background: #d4edda; border-color: #aed6b6; }
.chip.rejected { background: #f8d7da; border-color: #ecaab0; }
.chip.rejected strong { color: #721c24; }
.chip.pass { background: #e8f6ec; border-color: #b9d6c1; }
"""


def _read_json(p: Path) -> dict | None:
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _resolve_gap_dp(dp_id: str) -> dict | None:
    if not dp_id.startswith("skill_without_verifier:"):
        return None
    ds = DATASETS_DIR / "skill_without_verifier.jsonl"
    if not ds.is_file():
        return None
    for line in ds.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("id") == dp_id:
            return rec
    return None


def _esc(s: str) -> str:
    return _html.escape(str(s))


def _render_provenance(manifest: dict, gap_dp: dict | None, prev: dict | None) -> str:
    gap_collector = "—"; gap_ss = "—"; gap_collected_at = "—"; gap_collector_path = ""
    if gap_dp:
        gap_collector = gap_dp["provenance"]["collector"]["target"].get("collector_id", "—")
        gap_ss = gap_dp["provenance"].get("source_state", "—")[:24] + "…"
        gap_collected_at = gap_dp["provenance"].get("collected_at", "—")
        guess = REPO_ROOT / "skills" / "gap_audit" / "collectors" / f"{gap_collector}.py"
        if guess.is_file():
            gap_collector_path = f'<br><small>source: <code>skills/gap_audit/collectors/{_esc(gap_collector)}.py</code></small>'
    proposed_at = manifest.get("proposed_at", {}).get("source_state", "—")
    proposed_by = manifest.get("proposed_by", {}).get("target", {}).get("orchestration_id", "—")
    prev_at = (prev or {}).get("provenance", {}).get("collected_at", "—")
    return (
        '<div class="provenance">'
        f'<div class="prov-step"><strong>1. Gap measured</strong>by collector <code>{_esc(gap_collector)}</code>'
        f'{gap_collector_path}<br>at source_state <code>{_esc(gap_ss)}</code><br>on {_esc(gap_collected_at)}</div>'
        '<div class="prov-arrow">→</div>'
        f'<div class="prov-step"><strong>2. Proposal drafted</strong>by orchestration <code>{_esc(proposed_by)}</code><br>at <code>{_esc(proposed_at)}</code></div>'
        '<div class="prov-arrow">→</div>'
        f'<div class="prov-step"><strong>3. Pre-verification ran</strong>at {_esc(prev_at)}<br>against the candidate file</div>'
        '<div class="prov-arrow">→</div>'
        '<div class="prov-step"><strong>4. Awaits operator</strong>writes a line to <code>approvals/decisions.jsonl</code></div>'
        '</div>'
    )


def _render_checks(prev_value: dict) -> str:
    rows: list[str] = []
    checks = prev_value.get("checks", {})
    for cid, data in checks.items():
        verdict = data.get("verdict", "?")
        title, why = CHECK_GLOSSARY.get(cid, (cid, "(no glossary entry yet)"))
        details_bits: list[str] = []
        if "substantive_lines" in data:
            details_bits.append(f'<span class="metric">{data["substantive_lines"]}/{data.get("budget","?")} lines</span>')
        if "checks_passed" in data:
            details_bits.append(f'<span class="metric">{data["checks_passed"]}/{data.get("checks_total","?")} checks</span>')
        if "records_compared" in data:
            details_bits.append(f'<span class="metric">{data["records_compared"]} records compared</span>')
        if data.get("missing"):
            details_bits.append(f'<span class="no-data">missing: {_esc(", ".join(data["missing"]))}</span>')
        if data.get("banned_matches"):
            details_bits.append(f'<span class="no-data">banned: {_esc(", ".join(data["banned_matches"]))}</span>')
        details_html = " ".join(details_bits) if details_bits else ""
        rows.append(
            f'<tr><td><strong>{_esc(title)}</strong><br><code>{_esc(cid)}</code></td>'
            f'<td class="why">{_esc(why)}</td>'
            f'<td class="res"><span class="badge {_esc(verdict)}">{_esc(verdict)}</span> {details_html}</td></tr>'
        )
    return ('<table class="checks"><thead><tr><th>Check</th><th>What it verifies</th><th>Result</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def _render_proposal(prop_dir: Path) -> str:
    manifest = _read_json(prop_dir / "proposal.json") or {}
    gap = _read_json(prop_dir / "gap.json") or {}
    prev = _read_json(prop_dir / "pre_verification.json") or {}
    pid = manifest.get("proposal_id", prop_dir.name)
    status = manifest.get("status", "?")
    gap_dp = None
    if gap.get("gap_pointers"):
        gap_dp = _resolve_gap_dp(gap["gap_pointers"][0]["target"].get("data_point_id", ""))
    target_skill = "?"
    if gap_dp:
        target_skill = gap_dp["value"]["skill_pointer"]["target"]["path"]
    cand_path = manifest.get("candidate_pointer", {}).get("target", {}).get("path", "?")
    cand_id = manifest.get("candidate_pointer", {}).get("target", {}).get("collector_id", "?")
    cand_full = REPO_ROOT / cand_path
    line_count = sum(1 for _ in cand_full.read_text(encoding="utf-8").splitlines()) if cand_full.is_file() else 0
    preview_lines = []
    if cand_full.is_file():
        for i, line in enumerate(cand_full.read_text(encoding="utf-8").splitlines()[:30], start=1):
            preview_lines.append(f"{i:>3}  {line}")
    overall = (prev.get("value") or {}).get("overall_verdict", "?")
    parts = [f'<section class="proposal" id="{_esc(pid)}">']
    parts.append(f'<header class="proposal-header"><h2>{_esc(pid)}</h2>'
                 f'<div><span class="badge {_esc(status)}">status: {_esc(status)}</span> '
                 f'<span class="badge {_esc(overall)}">overall: {_esc(overall)}</span></div></header>')
    parts.append('<dl class="kv">')
    parts.append(f'<dt>Target skill</dt><dd><code>{_esc(target_skill)}</code></dd>')
    parts.append(f'<dt>Promotes to</dt><dd><code>{_esc(target_skill)}/verify.py</code></dd>')
    parts.append(f'<dt>Candidate</dt><dd><code>{_esc(cand_path)}</code> ({line_count} total lines, collector_id <code>{_esc(cand_id)}</code>)</dd>')
    parts.append(f'<dt>Claimed kind</dt><dd><code>{_esc(manifest.get("claimed_kind","?"))}</code></dd>')
    parts.append('</dl>')
    parts.append('<h3>Provenance trail</h3>')
    parts.append(_render_provenance(manifest, gap_dp, prev))
    if gap.get("narrative"):
        parts.append(f'<h3>The measured gap</h3><div class="gap-narrative">{_esc(gap["narrative"])}</div>')
    parts.append('<h3>Pre-verification — what was checked, in plain language</h3>')
    parts.append(_render_checks(prev.get("value", {})))
    if preview_lines:
        parts.append('<h3>Candidate source — first 30 lines</h3>')
        parts.append(f'<pre class="preview">{_esc(chr(10).join(preview_lines))}</pre>')
    parts.append('<details><summary>Promote / reject — copy-paste commands</summary><pre>')
    parts.append(_esc(f"# Promote (writes one line to approvals/decisions.jsonl, then runs the promoter):\n"
                      f"mkdir -p approvals\n"
                      f'echo \'{{"proposal_id":"{pid}","verdict":"promote","decided_at":"$(date -Iseconds)","by":"<you>"}}\' >> approvals/decisions.jsonl\n'
                      f"python -m tools.promote {pid} --dry-run   # preview\n"
                      f"python -m tools.promote {pid}             # execute\n\n"
                      f"# Reject (records the decision; no file move):\n"
                      f'echo \'{{"proposal_id":"{pid}","verdict":"reject","decided_at":"$(date -Iseconds)","by":"<you>","reason":"<short>"}}\' >> approvals/decisions.jsonl'))
    parts.append('</pre></details></section>')
    return "".join(parts)


def _summary_banner(dirs: list[Path]) -> str:
    if not dirs:
        return ""
    total = len(dirs)
    n_proposed = 0; n_promoted = 0; n_rejected = 0
    n_overall_pass = 0; n_overall_fail = 0
    target_skills: list[str] = []
    for d in dirs:
        m = _read_json(d / "proposal.json") or {}
        prev = _read_json(d / "pre_verification.json") or {}
        gap = _read_json(d / "gap.json") or {}
        s = m.get("status", "?")
        if s == "proposed": n_proposed += 1
        elif s == "promoted": n_promoted += 1
        elif s == "rejected": n_rejected += 1
        ov = (prev.get("value") or {}).get("overall_verdict", "?")
        if ov == "pass": n_overall_pass += 1
        elif ov == "fail": n_overall_fail += 1
        if gap.get("gap_pointers"):
            dp_id = gap["gap_pointers"][0]["target"].get("data_point_id", "")
            gap_dp = _resolve_gap_dp(dp_id)
            if gap_dp:
                target_skills.append(gap_dp["value"]["skill_pointer"]["target"]["path"])
    chips = [
        f'<span class="chip"><strong>{total}</strong> total</span>',
        f'<span class="chip proposed"><strong>{n_proposed}</strong> proposed</span>',
        f'<span class="chip promoted"><strong>{n_promoted}</strong> promoted</span>',
        f'<span class="chip rejected"><strong>{n_rejected}</strong> rejected</span>',
        f'<span class="chip pass"><strong>{n_overall_pass}/{total}</strong> pre-verifications pass</span>',
    ]
    growth_line = ""
    if n_proposed > 0 and target_skills:
        skill_list = ", ".join(f"<code>{_esc(s)}</code>" for s in target_skills if s != "?")
        growth_line = (f'<p><strong>Floor-growth potential:</strong> if all {n_proposed} pending proposals promote, '
                       f'<code>skill_without_verifier</code> gap inventory drains by {n_proposed} (currently 3 '
                       f'records, would become 0). Targets: {skill_list}. That round-over-round drain — '
                       f'measurable, anchored to source_state, reproducible — is the floor-growth signal '
                       f'CLAUDE.md names as the alternative to the vibecoding trap.</p>')
    return (f'<div class="summary"><h2 style="margin-top:0">Summary</h2>'
            f'<div class="chips">{"".join(chips)}</div>'
            f'{growth_line}</div>')


def _intro(n: int) -> str:
    return ('<div class="intro">'
            '<p><strong>What you\'re looking at.</strong> Each card below is a candidate <code>verify.py</code> '
            'drafted by the overnight loop in response to a measured gap. The provenance trail shows the chain '
            'of trust from <em>gap measured by a Foundation-2 collector</em> through <em>candidate drafted</em> '
            'through <em>pre-verification ran</em> to <em>awaiting operator</em>.</p>'
            '<p><strong>How to read it.</strong> The Pre-verification table explains every Foundation-2 check '
            'in plain language alongside its result. A green <span class="badge pass">pass</span> means the '
            'check ran cleanly at draft-time; the same checks run again at promotion-time, so a draft-pass '
            'is not a final pass.</p>'
            f'<p><strong>{n} pending proposal(s)</strong> below, sorted by proposal_id.</p></div>')


def _walk() -> str:
    if not PROPOSALS_DIR.is_dir():
        return _intro(0)
    dirs = sorted(d for d in PROPOSALS_DIR.iterdir() if d.is_dir() and (d / "proposal.json").is_file())
    body = [_summary_banner(dirs), _intro(len(dirs))]
    for d in dirs:
        body.append(_render_proposal(d))
    return "".join(body)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    doc = (f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
           f"<title>Proposals — Review</title><style>{CSS}</style></head>"
           f"<body><h1>Proposals — Review surface</h1>{_walk()}</body></html>")
    if args.stdout:
        sys.stdout.write(doc)
    else:
        out = PROPOSALS_DIR / "REVIEW.html"
        out.write_text(doc, encoding="utf-8")
        print(f"wrote {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
