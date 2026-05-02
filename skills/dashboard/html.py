"""Dashboard HTML render.

Self-contained HTML page (inline CSS, inline SVG sparkline, no JS, no
external assets). Same artifact substrate as render.py and narrate.py;
different surface — for browser viewing or sharing.

File path links use the vscode://file/ protocol so clicks open the source
in VSCode if the protocol handler is registered. Otherwise the path is
shown verbatim as a fallback.

Usage:
  python -m skills.dashboard.html               # print HTML to stdout
  python -m skills.dashboard.html -o page.html  # write to a file
"""
from __future__ import annotations

import datetime as _dt
import html as _html
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from skills.dashboard import snapshot as _snap  # noqa: E402


# ---------- helpers ----------


def _h(s) -> str:
    return _html.escape(str(s), quote=True)


def _link(rel_path: str, label: str | None = None) -> str:
    label = label or rel_path
    abs_path = (REPO / rel_path).resolve().as_posix()
    href = f"vscode://file/{abs_path}"
    return f'<a href="{_h(href)}" title="{_h(rel_path)}">{_h(label)}</a>'


def _badge(label: str, kind: str) -> str:
    return f'<span class="badge {_h(kind)}">{_h(label)}</span>'


def _sparkline(values: list[float], *, width: int = 220, height: int = 44) -> str:
    if not values or len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    rng = hi - lo if hi > lo else 1.0
    n = len(values)
    pad = 4
    plot_w = width - 2 * pad
    plot_h = height - 2 * pad
    pts = []
    for i, v in enumerate(values):
        x = pad + (i / (n - 1)) * plot_w
        y = pad + plot_h - ((v - lo) / rng) * plot_h
        pts.append(f"{x:.1f},{y:.1f}")
    last_x, last_y = pts[-1].split(",")
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'class="sparkline" aria-label="floor_ratio trend">'
        f'<polyline fill="none" stroke="#2563eb" stroke-width="2" '
        f'points="{" ".join(pts)}"/>'
        f'<circle cx="{last_x}" cy="{last_y}" r="3" fill="#2563eb"/>'
        f'</svg>'
    )


# ---------- sections ----------


CHECK_LABELS: dict[str, str] = {
    "audit_budget_under_80": "Stays under the 80-line budget",
    "candidate_runs_clean_against_target": "Runs cleanly against the live target",
    "determinism_runtime_check": "Determinism: same input → same output, twice",
    "no_llm_sdk_imports": "Imports no LLM SDK (anthropic, openai, etc.)",
    "no_nondeterminism_imports": "Imports nothing nondeterministic (random, time, uuid)",
    "required_constants_present": "Declares the required collector constants",
    "required_functions_present": "Declares the required collector functions",
}


def _check_evidence(name: str, body: dict) -> str:
    """Plain-language one-line evidence string for one pre-verification check."""
    if name == "audit_budget_under_80":
        return f'{body.get("substantive_lines", "?")} substantive lines vs. 80-line budget'
    if name == "candidate_runs_clean_against_target":
        return f'{body.get("checks_passed", "?")} of {body.get("checks_total", "?")} walker checks pass against target'
    if name == "determinism_runtime_check":
        n = body.get("records_compared", "?")
        return f'Ran collect() twice at same source_state → identical output across {n} records'
    if name == "no_llm_sdk_imports":
        imports = body.get("all_imports") or []
        if imports:
            return f'Imports: {", ".join(imports)} — no SDK match'
        return "No banned imports detected"
    if name == "no_nondeterminism_imports":
        note = body.get("note")
        if note:
            return note
        return "No banned imports detected"
    if name == "required_constants_present":
        found = body.get("found") or []
        return f'Found: {", ".join(found)}' if found else "—"
    if name == "required_functions_present":
        found = body.get("found") or []
        return f'Found: {", ".join(found)}' if found else "—"
    return ""


def _changes_panel(p: dict) -> str:
    """Small panel: what lands on disk if the operator authorizes."""
    cand = p.get("candidate_path") or ""
    target = p.get("target_verify_path") or ""
    lines = p.get("candidate_lines")
    target_exists = p.get("target_exists")
    target_state = (
        '<span class="badge attention">already exists</span>' if target_exists
        else '<span class="badge healthy">absent — would be created</span>'
    )
    cand_link = _link(cand, cand.split("/")[-1]) if cand else "—"
    target_link = _link(target, target) if target else "—"
    size_str = f"{lines} lines" if isinstance(lines, int) else "—"
    return (
        '<div class="panel"><div class="panel-title">If you approve, this lands on disk</div>'
        '<table class="kv"><tbody>'
        f'<tr><th>Action</th><td>copy file</td></tr>'
        f'<tr><th>Source</th><td>{cand_link} <span class="muted small">({_h(size_str)})</span></td></tr>'
        f'<tr><th>Destination</th><td><code>{_h(target)}</code> {target_state}</td></tr>'
        '</tbody></table></div>'
    )


def _checks_panel(p: dict) -> str:
    """Small panel: what the candidate's pre-verification actually verified."""
    pre = p.get("pre_verification") or {}
    checks = pre.get("checks") or {}
    if not checks:
        return ""
    rows = []
    for name in CHECK_LABELS:
        if name not in checks:
            continue
        body = checks[name]
        verdict = body.get("verdict") or "?"
        kind = "healthy" if verdict == "pass" else "attention"
        evidence = _check_evidence(name, body)
        rows.append(
            f'<tr><td>{_badge(verdict, kind)}</td>'
            f'<td><div class="check-label">{_h(CHECK_LABELS[name])}</div>'
            f'<div class="check-evidence muted small">{_h(evidence)}</div></td></tr>'
        )
    return (
        '<div class="panel"><div class="panel-title">Pre-verification — what was actually checked</div>'
        '<table class="checks"><tbody>'
        + "\n".join(rows)
        + '</tbody></table></div>'
    )


def _what_this_is_panel(p: dict) -> str:
    stakes = p.get("stakes") or {}
    text = stakes.get("what_this_is") or ""
    if not text:
        return (
            '<div class="panel stakes-missing">'
            '<div class="panel-title">What this is</div>'
            '<div class="muted small">Proposal lacks a <code>stakes.what_this_is</code> field — '
            'comprehension layer not authored.</div></div>'
        )
    return (
        '<div class="panel stakes-panel">'
        '<div class="panel-title">What this is</div>'
        f'<div class="stakes-text">{_h(text)}</div>'
        '</div>'
    )


def _why_panel(p: dict) -> str:
    """Why-we-build-it: pulled from stakes.why_we_build_it, not gap closure."""
    stakes = p.get("stakes") or {}
    text = stakes.get("why_we_build_it") or ""
    if not text:
        # fallback: derive from gap closure sentence
        gap = p.get("gap_narrative") or ""
        if "Closure:" in gap:
            text = gap.split("Closure:", 1)[1].strip().rstrip(".") + "."
        elif gap:
            text = gap.split(". ", 1)[0].rstrip(".") + "."
    if not text:
        return ""
    return (
        '<div class="panel stakes-panel">'
        '<div class="panel-title">Why we build it</div>'
        f'<div class="stakes-text">{_h(text)}</div>'
        '</div>'
    )


def _if_approved_panel(p: dict) -> str:
    bullets = (p.get("stakes") or {}).get("if_approved") or []
    if not bullets:
        return ""
    items = "".join(f'<li>{_h(b)}</li>' for b in bullets)
    return (
        '<div class="panel stakes-panel approve-stakes">'
        '<div class="panel-title">If you approve</div>'
        f'<ul class="stakes-list">{items}</ul>'
        '</div>'
    )


def _if_rejected_panel(p: dict) -> str:
    bullets = (p.get("stakes") or {}).get("if_rejected") or []
    if not bullets:
        return ""
    items = "".join(f'<li>{_h(b)}</li>' for b in bullets)
    return (
        '<div class="panel stakes-panel reject-stakes">'
        '<div class="panel-title">If you reject</div>'
        f'<ul class="stakes-list">{items}</ul>'
        '</div>'
    )


def _connects_to_panel(p: dict) -> str:
    items = (p.get("stakes") or {}).get("connects_to") or []
    if not items:
        return ""
    rows = []
    for item in items:
        path = item.get("path") or ""
        label = item.get("label") or path
        link = _link(path, path) if path else ""
        rows.append(
            f'<li><span class="connect-label">{_h(label)}</span> '
            f'<span class="muted small">— {link}</span></li>'
        )
    return (
        '<div class="panel stakes-panel connects-panel">'
        '<div class="panel-title">How this connects to other stuff</div>'
        f'<ul class="connects-list">{"".join(rows)}</ul>'
        '</div>'
    )


def _authorize_panel(p: dict) -> str:
    """Placeholder authorize affordance — the mechanism is unsettled.
    Visual area where a click-to-authorize would live; for now, it surfaces
    that the act is operator-owned and points at the open question."""
    pid = p["proposal_id"]
    return (
        '<div class="authorize-panel">'
        '<div class="panel-title">Authorize</div>'
        '<div class="authorize-row">'
        '<button class="auth-btn approve" disabled title="Mechanism not wired yet">Approve this proposal</button>'
        '<button class="auth-btn reject" disabled title="Mechanism not wired yet">Reject</button>'
        '</div>'
        '<div class="muted small auth-note">'
        f'Authorization mechanism for <code>{_h(pid)}</code> is not yet wired. '
        'You said you want to authorize your understanding, not run commands — '
        'the rebuilt panels above let you read the proposal as a dashboard; '
        'how you signal "I understand and approve" is the next decision.'
        '</div></div>'
    )


def _pending_decisions_section(snap: dict) -> str:
    pending = snap.get("pending_decisions", []) or []
    if not pending:
        return (
            '<section><h2>Awaiting your decision</h2>'
            '<p class="muted">No proposals are waiting on the operator. '
            'Drafts and design-previews live under '
            f'{_link("proposals/", "proposals/")} and surface here once they have '
            'a <code>proposal.json</code> at <code>status: proposed</code>.</p></section>'
        )
    cards = []
    for p in pending:
        pid = p["proposal_id"]
        target = p.get("target_skill_path") or "?"
        kind = p.get("claimed_kind") or "?"
        pre = p.get("pre_verification") or {}
        overall = pre.get("overall") or "?"
        budget = pre.get("audit_budget") or "?/?"
        passed = pre.get("checks_passed", 0)
        total = pre.get("checks_total", 0)
        overall_kind = "healthy" if overall == "pass" else "attention"
        target_link = _link(target, target) if target != "?" else _h(target)

        cards.append(
            '<div class="decision-card">'
            '<div class="decision-head">'
            f'<code class="pid">{_h(pid)}</code> '
            f'{_badge(overall, overall_kind)} '
            f'<span class="muted small">pre-verified {passed}/{total} · audit budget {_h(budget)}</span>'
            '</div>'
            '<div class="decision-sub muted small">'
            f'Target {target_link} · kind <code>{_h(kind)}</code>'
            '</div>'
            f'{_what_this_is_panel(p)}'
            f'{_why_panel(p)}'
            f'{_if_approved_panel(p)}'
            f'{_if_rejected_panel(p)}'
            f'{_changes_panel(p)}'
            f'{_connects_to_panel(p)}'
            f'{_checks_panel(p)}'
            f'{_authorize_panel(p)}'
            '</div>'
        )
    return (
        '<section class="pending-section">'
        f'<h2>Awaiting your decision <span class="count-badge">{len(pending)}</span></h2>'
        '<div class="section-intro">'
        '<div class="intro-title">What this section is</div>'
        '<p>'
        'Below are <strong>proposals</strong> — small bundles of code that one of the '
        'experiment\'s automated processes (gap-detection, overnight loops) wants to add '
        'to the live floor. The experiment\'s rules say only you, the operator, can sign '
        'off on a proposal landing on disk; the agent drafts and verifies, the operator '
        'authorizes.'
        '</p>'
        '<p>'
        f'Each card below answers, in order: <em>what is this thing</em>, <em>why we '
        'want it</em>, <em>what happens if you approve</em>, <em>what happens if you '
        'reject</em>, <em>what literally lands on disk</em>, <em>how it connects to '
        'other parts of the experiment</em>, and finally <em>the pre-verification '
        'evidence that the candidate is sound</em>. Read top-to-bottom; the first four '
        'panels are the comprehension layer, the last three are the evidence layer.'
        '</p>'
        '</div>'
        + "\n".join(cards)
        + '</section>'
    )


def _bedrock_section(snap: dict) -> str:
    rows = []
    for path, obs in snap.get("bedrock", {}).items():
        if obs.get("exists"):
            mark = _badge("OK", "healthy")
            mt = _h(obs.get("mtime_iso", ""))
            sha = _h((obs.get("sha256") or "")[:8])
            sz = _h(f'{obs.get("size_bytes", 0):,} B')
            rows.append(
                f"<tr><td>{_link(path, path.split('/')[-1].replace('.md',''))}</td>"
                f"<td><code>{_h(path)}</code></td>"
                f"<td>{mt}</td><td>{sz}</td><td><code>{sha}</code></td>"
                f"<td>{mark}</td></tr>"
            )
        else:
            rows.append(
                f"<tr><td>{_h(path)}</td><td colspan='4'>—</td>"
                f"<td>{_badge('MISSING', 'attention')}</td></tr>"
            )
    return (
        '<section><h2>Bedrock primitives</h2>'
        '<table><thead><tr>'
        '<th>Spec</th><th>Path</th><th>Last modified</th><th>Size</th>'
        '<th>SHA256 (8)</th><th>Status</th>'
        '</tr></thead><tbody>'
        + "\n".join(rows)
        + '</tbody></table></section>'
    )


def _floor_section(snap: dict) -> str:
    history = _snap._audit_history()
    audit = snap.get("audit", {})
    fr = audit.get("latest_floor_ratio")
    by_regime = audit.get("latest_by_regime", {})
    n = audit.get("bundle_count", 0)
    if fr is None:
        return ('<section><h2>Floor ratio</h2>'
                '<p class="muted">No audit bundles yet — run '
                '<code>python -m skills.regime_audit.orchestrate</code>.</p></section>')

    fr_str = f"{fr:.3f}"
    first = audit.get("first_floor_ratio")

    # Trend stats + sparkline
    series = [b["floor_ratio"] for b in history if isinstance(b.get("floor_ratio"), (int, float))]
    spark = _sparkline(series) if len(series) >= 2 else ""
    direction_html = ""
    if isinstance(first, (int, float)) and isinstance(fr, (int, float)) and n > 1:
        delta = fr - first
        cls = "healthy" if delta > 0 else ("muted" if abs(delta) < 0.0005 else "attention")
        word = "growing" if delta > 0 else ("flat" if abs(delta) < 0.0005 else "shrinking")
        direction_html = (
            f'<div class="trend-meta"><span class="badge {cls}">{_h(word)}</span> '
            f'<span class="muted">{first:.3f} → {fr_str} '
            f'across {n} runs ({delta:+.3f})</span></div>'
        )

    # Regime distribution table
    regime_order = ["bedrock", "0.0", "0.1", "0.2", "0.3", "unclassified"]
    regime_rows = []
    for r in regime_order:
        if r in by_regime:
            regime_rows.append(f"<tr><td>{_h(r)}</td><td class='num'>{by_regime[r]}</td></tr>")
    leftover = [r for r in by_regime if r not in regime_order]
    for r in sorted(leftover):
        regime_rows.append(f"<tr><td>{_h(r)}</td><td class='num'>{by_regime[r]}</td></tr>")

    # Trend table (bundle-by-bundle)
    trend_rows = []
    for b in history:
        bid = b["bundle_id"]
        rel = f"skills/regime_audit/outputs/{bid}/stats.json"
        fr_v = b.get("floor_ratio")
        fr_render = f"{fr_v:.3f}" if isinstance(fr_v, (int, float)) else "-"
        br = b.get("by_regime", {})
        trend_rows.append(
            f"<tr><td>{_link(rel, bid)}</td>"
            f"<td class='num'>{fr_render}</td>"
            f"<td class='num'>{br.get('0.1', 0)}</td>"
            f"<td class='num'>{br.get('0.2', 0)}</td>"
            f"<td class='num'>{br.get('0.3', 0)}</td></tr>"
        )

    latest_bid = audit.get("latest_bundle_id", "")
    latest_link = _link(f"skills/regime_audit/outputs/{latest_bid}/stats.json", latest_bid) if latest_bid else ""

    return (
        '<section><h2>Floor ratio</h2>'
        '<div class="floor-row">'
          '<div class="floor-headline">'
            f'<div class="big-number">{_h(fr_str)}</div>'
            '<div class="muted">latest floor_ratio</div>'
            f'{direction_html}'
            f'<div class="muted small">source: {latest_link}</div>'
          '</div>'
          f'<div class="spark-wrap">{spark}</div>'
          '<div class="regime-wrap">'
            '<table class="compact"><thead><tr><th>Regime</th><th>Count</th></tr></thead>'
            f'<tbody>{"".join(regime_rows)}</tbody></table>'
          '</div>'
        '</div>'
        '<details><summary>Trend across all bundles</summary>'
        '<table><thead><tr>'
        '<th>Bundle</th><th>floor_ratio</th><th>0.1</th><th>0.2</th><th>0.3</th>'
        '</tr></thead><tbody>'
        + "\n".join(trend_rows)
        + '</tbody></table></details>'
        '<p class="muted small">Definition: <code>(0.1 + 0.2) / 0.3</code> — substrate-to-free-write ratio. '
        'Growing means the floor is compounding.</p>'
        '</section>'
    )


def _boards_section(snap: dict) -> str:
    boards = snap.get("boards", {})
    if not boards:
        return '<section><h2>Boards</h2><p class="muted">No boards.</p></section>'
    rows = []
    for name in sorted(boards):
        b = boards[name]
        lb_open = b.get("load_bearing_open", 0)
        kind = "attention" if lb_open > 0 else "healthy"
        status_label = "needs_attention" if lb_open > 0 else "healthy"
        ids = b.get("load_bearing_open_ids", [])
        ids_html = ", ".join(_h(i) for i in ids) if ids else "—"
        last = b.get("last_activity") or "—"
        rows.append(
            f"<tr><td><code>{_h(name)}</code></td>"
            f"<td>{_badge(status_label, kind)}</td>"
            f"<td class='num'>{b.get('total', 0)}</td>"
            f"<td class='num'>{b.get('open', 0)}</td>"
            f"<td class='num'>{lb_open}</td>"
            f"<td>{ids_html}</td>"
            f"<td>{_h(last)}</td></tr>"
        )
    return (
        '<section><h2>Boards</h2>'
        '<table><thead><tr>'
        '<th>Board</th><th>Status</th><th>Total</th><th>Open</th>'
        '<th>Load-bearing-open</th><th>Open ids (load-bearing)</th><th>Last activity</th>'
        '</tr></thead><tbody>'
        + "\n".join(rows)
        + '</tbody></table>'
        '<p class="muted small">Drill in: <code>python -m boards &lt;name&gt;</code></p>'
        '</section>'
    )


def _leashes_section(snap: dict) -> str:
    leashes = snap.get("leashes", {})
    if not leashes:
        return '<section><h2>Leashes</h2><p class="muted">No leash skills.</p></section>'
    rows = []
    for name in sorted(leashes):
        l = leashes[name]
        state = l.get("state") or "?"
        toggle_kind = {"on": "healthy", "off": "attention", "scoped": "scoped"}.get(state, "muted")
        rel = f"skills/{name}/SKILL.md"
        rows.append(
            f"<tr><td>{_link(rel, name)}</td>"
            f"<td>{_badge(state, toggle_kind)}</td>"
            f"<td class='num'>{l.get('proposed', 0)}</td>"
            f"<td class='num'>{l.get('promoted', 0)}</td>"
            f"<td class='num'>{l.get('outputs', 0)}</td></tr>"
        )
    return (
        '<section><h2>Leashes</h2>'
        '<table><thead><tr>'
        '<th>Leash</th><th>Toggle</th><th>Proposed</th><th>Promoted</th><th>Output bundles</th>'
        '</tr></thead><tbody>'
        + "\n".join(rows)
        + '</tbody></table></section>'
    )


def _skills_regime_section(snap: dict) -> str:
    by_skill = snap.get("audit", {}).get("latest_by_skill", {})
    if not by_skill:
        return '<section><h2>Skills — regime distribution</h2><p class="muted">No audit data.</p></section>'
    regimes = ["bedrock", "0.0", "0.1", "0.2", "0.3", "unclassified"]
    rows = []
    for skill in sorted(by_skill):
        counts = by_skill[skill]
        total = sum(counts.values())
        cells = []
        for r in regimes:
            v = counts.get(r, 0)
            cls = "num"
            if r == "unclassified" and v > 0:
                cls += " attention-cell"
            cells.append(f"<td class='{cls}'>{v}</td>")
        rows.append(
            f"<tr><td><code>{_h(skill)}</code></td>"
            + "".join(cells)
            + f"<td class='num strong'>{total}</td></tr>"
        )
    return (
        '<section><h2>Skills — regime distribution</h2>'
        '<table><thead><tr>'
        '<th>Skill</th>'
        + "".join(f"<th>{_h(r)}</th>" for r in regimes)
        + '<th>Total</th>'
        '</tr></thead><tbody>'
        + "\n".join(rows)
        + '</tbody></table>'
        '<p class="muted small">Cells flagged red are unclassified — '
        'the regime_audit rule table has a gap there.</p>'
        '</section>'
    )


# ---------- top-level page ----------


CSS = """
:root {
  --bg: #0b1220;
  --panel: #111a2e;
  --panel-2: #16213a;
  --text: #e6edf7;
  --muted: #8aa0c0;
  --border: #233455;
  --accent: #60a5fa;
  --accent-2: #2563eb;
  --healthy-bg: #103a2a;
  --healthy-fg: #6ee7b7;
  --attention-bg: #3a1414;
  --attention-fg: #fda4af;
  --scoped-bg: #3a2c10;
  --scoped-fg: #fde68a;
  --code-bg: #1d2a47;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.45;
  font-size: 14px;
}
.container { max-width: 1100px; margin: 0 auto; padding: 32px 24px 64px; }
h1 { font-size: 22px; margin: 0 0 4px; }
h2 { font-size: 16px; margin: 28px 0 10px; padding-bottom: 6px; border-bottom: 1px solid var(--border); }
.subtitle { color: var(--muted); margin-bottom: 8px; }
.subtitle code { color: var(--accent); }
section { margin-bottom: 12px; }
table { width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
th, td { padding: 8px 12px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
thead th { background: var(--panel-2); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
tbody tr:last-child td { border-bottom: none; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
td.attention-cell { background: rgba(253, 164, 175, 0.10); color: var(--attention-fg); font-weight: 600; }
td.strong { font-weight: 600; }
code { background: var(--code-bg); padding: 1px 6px; border-radius: 3px; font-size: 12.5px; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.muted { color: var(--muted); }
.small { font-size: 12px; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; letter-spacing: 0.03em; }
.badge.healthy { background: var(--healthy-bg); color: var(--healthy-fg); }
.badge.attention { background: var(--attention-bg); color: var(--attention-fg); }
.badge.scoped { background: var(--scoped-bg); color: var(--scoped-fg); }
.floor-row { display: grid; grid-template-columns: minmax(220px, 1fr) auto minmax(180px, auto); gap: 24px; align-items: center; padding: 16px; background: var(--panel); border: 1px solid var(--border); border-radius: 6px; margin-bottom: 12px; }
.floor-headline .big-number { font-size: 44px; font-weight: 700; line-height: 1; letter-spacing: -0.02em; }
.trend-meta { margin-top: 8px; }
.spark-wrap { display: flex; justify-content: center; }
.regime-wrap table { background: transparent; border: none; }
.regime-wrap th, .regime-wrap td { padding: 4px 10px; }
.regime-wrap thead th { background: transparent; }
details summary { cursor: pointer; padding: 6px 0; color: var(--muted); }
details[open] summary { color: var(--text); margin-bottom: 8px; }
.compact th, .compact td { padding: 4px 10px; font-size: 12px; }
.legend { color: var(--muted); font-size: 12px; margin-top: 8px; }

/* pending-decisions section */
.pending-section h2 { border-bottom-color: var(--accent); }
.count-badge {
  display: inline-block; min-width: 22px; padding: 1px 8px; margin-left: 8px;
  border-radius: 999px; background: var(--accent-2); color: white;
  font-size: 12px; font-weight: 700; text-align: center; vertical-align: 2px;
}
.decision-card {
  background: var(--panel); border: 1px solid var(--border);
  border-left: 3px solid var(--accent); border-radius: 6px;
  padding: 14px 16px; margin: 12px 0;
}
.decision-head { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 4px; }
.decision-head .pid { font-size: 13px; }
.decision-sub { margin-bottom: 12px; }

/* section-level intro */
.section-intro {
  background: var(--panel-2); border: 1px solid var(--border); border-radius: 6px;
  padding: 14px 16px; margin: 12px 0 18px;
}
.section-intro .intro-title {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--accent); font-weight: 600; margin-bottom: 8px;
}
.section-intro p { margin: 6px 0; font-size: 13px; line-height: 1.55; color: var(--text); }
.section-intro em { color: var(--accent); font-style: normal; font-weight: 600; }

/* small dashboard panels inside a decision card */
.panel {
  background: var(--panel-2); border: 1px solid var(--border); border-radius: 4px;
  padding: 10px 12px; margin: 8px 0;
}
.panel-title {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--muted); font-weight: 600; margin-bottom: 6px;
}

/* stakes panels: what-this-is, why, if-approved, if-rejected, connects-to */
.stakes-panel .stakes-text { font-size: 13px; color: var(--text); line-height: 1.55; }
.stakes-list, .connects-list { margin: 4px 0 0; padding-left: 20px; }
.stakes-list li, .connects-list li {
  font-size: 13px; color: var(--text); line-height: 1.5; margin: 4px 0;
}
.approve-stakes { border-left: 3px solid var(--healthy-fg); }
.approve-stakes .panel-title { color: var(--healthy-fg); }
.reject-stakes { border-left: 3px solid var(--attention-fg); }
.reject-stakes .panel-title { color: var(--attention-fg); }
.connects-panel { border-left: 3px solid var(--accent); }
.connects-panel .panel-title { color: var(--accent); }
.connect-label { color: var(--text); }
.stakes-missing { border-left: 3px solid var(--attention-fg); opacity: 0.85; }

/* key-value mini-table inside a panel */
table.kv { background: transparent; border: none; width: auto; margin: 0; }
table.kv th, table.kv td {
  border: none; padding: 3px 14px 3px 0; font-size: 13px; vertical-align: top;
}
table.kv th {
  background: transparent; color: var(--muted); font-weight: 500;
  text-transform: none; letter-spacing: 0; font-size: 12px; min-width: 100px;
}

/* checks table — verdict badge | label + evidence */
table.checks { background: transparent; border: none; margin: 0; }
table.checks tr { border: none; }
table.checks td {
  border: none; border-top: 1px solid var(--border);
  padding: 8px 12px 8px 0; vertical-align: top;
}
table.checks tr:first-child td { border-top: none; }
table.checks td:first-child { width: 64px; }
.check-label { font-size: 13px; color: var(--text); }
.check-evidence { margin-top: 2px; line-height: 1.4; }

/* authorize affordance */
.authorize-panel {
  background: var(--panel-2); border: 1px dashed var(--accent); border-radius: 4px;
  padding: 12px 14px; margin: 12px 0 0;
}
.authorize-row { display: flex; gap: 10px; margin: 6px 0 8px; }
.auth-btn {
  font: inherit; padding: 8px 16px; border-radius: 4px; border: 1px solid var(--border);
  cursor: not-allowed; font-weight: 600; font-size: 13px;
}
.auth-btn.approve { background: var(--healthy-bg); color: var(--healthy-fg); border-color: var(--healthy-fg); }
.auth-btn.reject { background: var(--attention-bg); color: var(--attention-fg); border-color: var(--attention-fg); }
.auth-btn[disabled] { opacity: 0.55; }
.auth-note { line-height: 1.5; }
"""


def render_html(snap: dict) -> str:
    title = "zero-four-experiment — operator dashboard"
    captured = snap.get("captured_at", "")
    parts = [
        '<!doctype html>',
        '<html lang="en">',
        '<head>',
        '<meta charset="utf-8">',
        f'<title>{_h(title)}</title>',
        f'<style>{CSS}</style>',
        '</head>',
        '<body>',
        '<div class="container">',
        f'<h1>{_h(title)}</h1>',
        f'<div class="subtitle">Captured <code>{_h(captured)}</code> · highest abstraction: {_link("CLAUDE.md")}</div>',
        _pending_decisions_section(snap),
        _bedrock_section(snap),
        _floor_section(snap),
        _boards_section(snap),
        _leashes_section(snap),
        _skills_regime_section(snap),
        '<p class="legend">'
        'Source links use the <code>vscode://file/</code> protocol. '
        'Click jumps to the file in VSCode if the protocol handler is registered. '
        'This page is self-contained — no external assets, no JS, no network.'
        '</p>',
        '</div>',
        '</body>',
        '</html>',
    ]
    return "\n".join(parts) + "\n"


def main() -> int:
    args = sys.argv[1:]
    out_path: Path | None = None
    if "-o" in args:
        i = args.index("-o")
        if i + 1 >= len(args):
            print("usage: python -m skills.dashboard.html [-o <path>]", file=sys.stderr)
            return 2
        out_path = Path(args[i + 1])

    snap = _snap.gather()
    page = render_html(snap)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page, encoding="utf-8")
        sys.stderr.write(f"wrote {out_path}\n")
    else:
        sys.stdout.write(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
