"""Dashboard narrate: delta-aware narrative render.

Compares the current live state to the last persisted snapshot in
skills/dashboard/outputs/run-*/. Emits prose paragraphs covering:

  - Floor (floor_ratio movement, new 0.1/0.2/0.3 components since last snapshot)
  - Boards (which boards moved; which load-bearing items closed/opened)
  - Leashes (toggle changes, exemplar promotion movement)
  - Bedrock (any spec hash changed since last snapshot)
  - What likely needs attention next (rule-based, not LLM-generated)

By default also persists the new snapshot at the end so subsequent narrates
have something to compare against. Pass --no-save to skip the write.

Usage:
  python -m skills.dashboard.narrate
  python -m skills.dashboard.narrate --no-save
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from skills.dashboard import snapshot as _snap  # noqa: E402


# ---------- delta helpers ----------


def _delta_int(prev, cur) -> str:
    """Render an int delta as ' (+N)' / ' (-N)' / ''."""
    if prev is None or cur is None:
        return ""
    d = cur - prev
    if d == 0:
        return ""
    return f" ({d:+d})"


def _delta_float(prev, cur, places: int = 3) -> str:
    if prev is None or cur is None:
        return ""
    d = cur - prev
    if abs(d) < 0.0005:
        return ""
    return f" ({d:+.{places}f})"


def _list_diff(prev_ids: list[str], cur_ids: list[str]) -> tuple[list[str], list[str]]:
    prev_set = set(prev_ids)
    cur_set = set(cur_ids)
    added = sorted(cur_set - prev_set)
    removed = sorted(prev_set - cur_set)
    return added, removed


def _regime_delta(prev_by_regime: dict, cur_by_regime: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    keys = set(prev_by_regime) | set(cur_by_regime)
    for k in keys:
        d = cur_by_regime.get(k, 0) - prev_by_regime.get(k, 0)
        if d != 0:
            out[k] = d
    return out


# ---------- narrative sections ----------


def _section_floor(cur: dict, prev: dict | None) -> list[str]:
    cur_audit = cur.get("audit", {})
    cur_fr = cur_audit.get("latest_floor_ratio")
    bundle_n = cur_audit.get("bundle_count", 0)
    first_fr = cur_audit.get("first_floor_ratio")

    lines = ["**Floor.**"]
    if cur_fr is None:
        lines.append("No audit bundles yet — the regime distribution is unknown. Run `python -m skills.regime_audit.orchestrate`.")
        return lines

    fr_str = f"{cur_fr:.3f}"
    if first_fr is not None and bundle_n > 1:
        delta = cur_fr - first_fr
        direction = "growing" if delta > 0 else ("flat" if abs(delta) < 0.0005 else "shrinking")
        lines.append(f"floor_ratio = {fr_str} after {bundle_n} audit runs ({first_fr:.3f} → {fr_str}, {direction}, {delta:+.3f}).")
    else:
        lines.append(f"floor_ratio = {fr_str} (first audit; no trend yet).")

    if prev:
        prev_audit = prev.get("audit", {})
        prev_fr = prev_audit.get("latest_floor_ratio")
        if prev_fr is not None and abs(cur_fr - prev_fr) >= 0.0005:
            lines.append(f"Since last snapshot: {prev_fr:.3f} → {fr_str}{_delta_float(prev_fr, cur_fr)}.")
        elif prev_fr is not None:
            lines.append(f"Unchanged since last snapshot ({prev_fr:.3f}).")

        regime_d = _regime_delta(
            prev_audit.get("latest_by_regime", {}),
            cur_audit.get("latest_by_regime", {}),
        )
        if regime_d:
            parts = [f"{k} {v:+d}" for k, v in sorted(regime_d.items())]
            lines.append(f"Regime shifts: {', '.join(parts)}.")

    return lines


def _section_boards(cur: dict, prev: dict | None) -> list[str]:
    cur_b = cur.get("boards", {})
    if not cur_b:
        return ["**Boards.**", "No boards configured."]

    lines = ["**Boards.**"]
    for name in sorted(cur_b):
        c = cur_b[name]
        p = (prev or {}).get("boards", {}).get(name) if prev else None

        lb_open_cur = c.get("load_bearing_open", 0)
        open_cur = c.get("open", 0)
        total_cur = c.get("total", 0)
        ids_cur = c.get("load_bearing_open_ids", [])

        if p:
            lb_open_prev = p.get("load_bearing_open", 0)
            open_prev = p.get("open", 0)
            total_prev = p.get("total", 0)
            ids_prev = p.get("load_bearing_open_ids", [])
            added, removed = _list_diff(ids_prev, ids_cur)
            line = (
                f"- `{name}`: {total_cur} total{_delta_int(total_prev, total_cur)}, "
                f"{open_cur} open{_delta_int(open_prev, open_cur)}, "
                f"{lb_open_cur} load-bearing-open{_delta_int(lb_open_prev, lb_open_cur)}"
            )
            tag_parts = []
            if added:
                tag_parts.append(f"opened load-bearing: {', '.join(added)}")
            if removed:
                tag_parts.append(f"closed load-bearing: {', '.join(removed)}")
            if tag_parts:
                line += "  — " + "; ".join(tag_parts)
            lines.append(line + ".")
        else:
            line = f"- `{name}`: {total_cur} total, {open_cur} open, {lb_open_cur} load-bearing-open"
            if ids_cur:
                line += f" ({', '.join(ids_cur)})"
            lines.append(line + ".")
    return lines


def _section_leashes(cur: dict, prev: dict | None) -> list[str]:
    cur_l = cur.get("leashes", {})
    if not cur_l:
        return ["**Leashes.**", "No leash skills present."]

    lines = ["**Leashes.**"]
    for name in sorted(cur_l):
        c = cur_l[name]
        p = (prev or {}).get("leashes", {}).get(name) if prev else None
        toggle = c.get("state") or "?"
        proposed = c.get("proposed", 0)
        promoted = c.get("promoted", 0)
        outputs = c.get("outputs", 0)
        if p:
            prev_toggle = p.get("state")
            toggle_note = ""
            if prev_toggle != toggle and prev_toggle is not None:
                toggle_note = f" (was **{prev_toggle}**)"
            line = (
                f"- `{name}`: toggle **{toggle}**{toggle_note}, "
                f"{proposed} proposed{_delta_int(p.get('proposed', 0), proposed)}, "
                f"{promoted} promoted{_delta_int(p.get('promoted', 0), promoted)}, "
                f"{outputs} output bundles{_delta_int(p.get('outputs', 0), outputs)}."
            )
        else:
            line = f"- `{name}`: toggle **{toggle}**, {proposed} proposed, {promoted} promoted, {outputs} output bundles."
        lines.append(line)
    return lines


def _section_bedrock(cur: dict, prev: dict | None) -> list[str]:
    cur_b = cur.get("bedrock", {})
    lines = ["**Bedrock.**"]
    missing = [p for p, obs in cur_b.items() if not obs.get("exists")]
    if missing:
        lines.append("**MISSING SPECS** — " + ", ".join(missing) + ". Bootstrap order broken; do not proceed.")
        return lines
    if prev:
        prev_b = prev.get("bedrock", {})
        changed = []
        for path, obs in cur_b.items():
            prev_obs = prev_b.get(path, {})
            if prev_obs.get("sha256") and obs.get("sha256") != prev_obs.get("sha256"):
                changed.append(path)
        if changed:
            lines.append(
                "**Spec hash changed** since last snapshot: " + ", ".join(changed) +
                ". Per the foundations, any change to a bedrock spec is itself a 0.4 grading event. Log it explicitly."
            )
            return lines
    lines.append(f"All {len(cur_b)} foundation specs present and unchanged.")
    return lines


def _section_attention(cur: dict, prev: dict | None) -> list[str]:
    """Rule-based suggestions. No LLM — explicit conditions on snapshot fields."""
    suggestions: list[str] = []

    # Rule 1: any load-bearing-open debts → call them out by id
    debts = cur.get("boards", {}).get("debts", {})
    lb_ids = debts.get("load_bearing_open_ids", [])
    if lb_ids:
        suggestions.append(
            f"Load-bearing debts still open: {', '.join(lb_ids)}. "
            f"Drill in with `python -m boards debts`."
        )

    # Rule 2: high proposed-vs-promoted exemplar imbalance per leash
    for name, l in cur.get("leashes", {}).items():
        proposed = l.get("proposed", 0)
        promoted = l.get("promoted", 0)
        if proposed >= 3 and promoted == 0:
            suggestions.append(
                f"`{name}` has {proposed} exemplars proposed and 0 promoted — "
                f"the promotion gate is the bottleneck if you want to ramp this leash."
            )

    # Rule 3: floor flat across recent runs
    audit = cur.get("audit", {})
    by_regime = audit.get("latest_by_regime", {})
    n = audit.get("bundle_count", 0)
    fr_first = audit.get("first_floor_ratio")
    fr_last = audit.get("latest_floor_ratio")
    if (
        n >= 3 and isinstance(fr_first, (int, float)) and isinstance(fr_last, (int, float))
        and abs(fr_last - fr_first) < 0.001
    ):
        suggestions.append(
            f"Floor ratio is flat across {n} runs ({fr_last:.3f}). "
            f"Substrate not growing — consider adding a 0.1 collector or 0.2 signal."
        )

    # Rule 4: 0.3 grew without 0.1 since last snapshot
    if prev:
        prev_audit = prev.get("audit", {})
        prev_regime = prev_audit.get("latest_by_regime", {})
        d3 = by_regime.get("0.3", 0) - prev_regime.get("0.3", 0)
        d1 = by_regime.get("0.1", 0) - prev_regime.get("0.1", 0)
        if d3 > 0 and d1 <= 0:
            suggestions.append(
                f"0.3 grew by {d3} without matching 0.1 growth ({d1:+d}) since last snapshot — "
                f"free-write share is rising."
            )

    # Rule 5: any leash toggle is off
    for name, l in cur.get("leashes", {}).items():
        if l.get("state") == "off":
            suggestions.append(
                f"`{name}` toggle is **off** — the agent is autonomous on that surface. "
                f"Verify trust is established."
            )

    if not suggestions:
        return ["**What likely needs attention next.**", "Nothing flagged by the rule set."]
    return ["**What likely needs attention next.**"] + [f"- {s}" for s in suggestions]


# ---------- top-level ----------


def narrate(cur: dict, prev: dict | None) -> str:
    today = cur.get("captured_at", "")[:10]
    head = [
        "# zero-four-experiment — narrative status",
        "",
        f"_Captured {cur.get('captured_at', '?')}._  ",
    ]
    if prev:
        head.append(f"Comparing against snapshot at _{prev.get('captured_at', '?')}_.")
    else:
        head.append("No prior snapshot — this is the baseline.")
    head.append("")

    parts: list[list[str]] = [
        _section_floor(cur, prev),
        _section_boards(cur, prev),
        _section_leashes(cur, prev),
        _section_bedrock(cur, prev),
        _section_attention(cur, prev),
    ]
    body: list[str] = []
    for sec in parts:
        body.extend(sec)
        body.append("")
    return "\n".join(head + body).rstrip() + "\n"


def main() -> int:
    save = "--no-save" not in sys.argv[1:]
    cur = _snap.gather()
    prev = _snap.find_latest_persisted()
    print(narrate(cur, prev))
    if save:
        path = _snap.persist(cur)
        rel = path.relative_to(REPO).as_posix()
        sys.stderr.write(f"\n(snapshot persisted: {rel})\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
