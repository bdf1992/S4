"""Trace conformity health snapshot.

Walks orchestration_audit's activations dataset, groups activation rows
by (skill_id, run_id) into per-run traces, calls trace_conformity.evaluate()
on each trace, and prints an aggregate verdict distribution + per-skill
breakdown + missing-target-class gap roll-up.

Importing skills.orchestration_audit.signals.trace_conformity at module
top — and calling evaluate() on real traces — graduates orchestration_audit
from isolated_with_signals to graduated under floor_growth's classifier
(this file becomes the first peer signals consumer in tools/). Removing
the import would unwire that fence and floor_growth would re-flag.

The dataset path is resolved against orchestration_audit's collector
output. If the dataset is missing or stale, the renderer says so and
exits 0; that is the floor's own way of naming the gap, not a failure.

Run:
  python -m tools.trace_health         # health summary over current corpus
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from skills.orchestration_audit.signals import trace_conformity

REPO = Path(__file__).resolve().parents[1]
ACTIVATIONS = REPO / "skills" / "orchestration_audit" / "datasets" / "orchestration_activations.jsonl"


def _load_activations() -> list[dict]:
    if not ACTIVATIONS.is_file():
        return []
    out: list[dict] = []
    for line in ACTIVATIONS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line)["value"])
    return out


def _group_by_run(rows: list[dict]) -> list[tuple[str, str, str, list[dict]]]:
    """Returns [(skill_id, run_id, run_claim, sorted_trace), ...]."""
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    claims: dict[tuple[str, str], str] = {}
    for r in rows:
        key = (r["skill_id"], r["run_id"])
        groups[key].append(r)
        claims[key] = r.get("run_claim", "")
    out: list[tuple[str, str, str, list[dict]]] = []
    for key, acts in groups.items():
        trace = sorted(acts, key=lambda a: a.get("sequence_index", 0))
        out.append((key[0], key[1], claims[key], trace))
    return sorted(out, key=lambda t: (t[0], t[1]))


def render() -> str:
    rows = _load_activations()
    groups = _group_by_run(rows)

    lines = ["# Trace conformity health — orchestration_audit signal evaluated over corpus", ""]
    if not groups:
        lines.append("_no orchestration_activations dataset present;_")
        lines.append("_run `python -m skills.orchestration_audit.collectors.orchestration_activations` first._")
        return "\n".join(lines)

    verdict_counts: Counter = Counter()
    by_skill: dict[str, Counter] = defaultdict(Counter)
    confidences: list[float] = []
    missing_target: Counter = Counter()

    for skill, run, claim, trace in groups:
        result = trace_conformity.evaluate(trace)
        verdict_counts[result["verdict"]] += 1
        by_skill[skill][result["verdict"]] += 1
        confidences.append(result["confidence"])
        gap = result.get("gap_record", {}) or {}
        m = gap.get("missing_target_class")
        if m:
            missing_target[m] += 1

    total = sum(verdict_counts.values())
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    lines.append(f"runs evaluated: **{total}**  ·  mean confidence: **{avg_conf:.4f}**")
    lines.append("")
    lines.append("## Verdict distribution")
    lines.append("")
    lines.append("| verdict | count |")
    lines.append("| --- | --: |")
    for v in ("ready", "inconclusive", "not_ready"):
        lines.append(f"| `{v}` | {verdict_counts.get(v, 0)} |")
    lines.append("")

    if missing_target:
        lines.append("## Gap records — missing target classes")
        lines.append("")
        for cls, n in missing_target.most_common():
            lines.append(f"- `{cls}` missing in **{n}** runs' corpus")
        lines.append("")

    lines.append("## By skill")
    lines.append("")
    lines.append("| skill | ready | inconclusive | not_ready |")
    lines.append("| --- | --: | --: | --: |")
    for skill in sorted(by_skill):
        c = by_skill[skill]
        lines.append(
            f"| `{skill}` | {c.get('ready', 0)} | "
            f"{c.get('inconclusive', 0)} | {c.get('not_ready', 0)} |"
        )

    return "\n".join(lines)


def main() -> int:
    print(render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
