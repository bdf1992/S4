"""Renders a regime_audit stats bundle into a human-viewable markdown report.

Pure 0.1 transform: stats.json -> report.md. Deterministic, no LLM, no
nondeterminism. Decoupled from regime_audit so that the artifact format
and the view format can evolve independently.

Usage:
  python -m skills.regime_audit_report.render <bundle-dir>
  python -m skills.regime_audit_report.render --latest        # most recent bundle
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REGIME_ORDER = ("bedrock", "0.0", "0.1", "0.2", "0.3", "unclassified")
REGIME_LABELS = {
    "bedrock": "Bedrock (immutable specs)",
    "0.0": "0.0 — prose / docs",
    "0.1": "0.1 — deterministic programs",
    "0.2": "0.2 — statistical signals",
    "0.3": "0.3 — orchestration / LLM-using",
    "unclassified": "Unclassified",
}

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUNDLES_DIR = REPO_ROOT / "skills" / "regime_audit" / "outputs"


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join(["---"] * len(headers)) + " |"]
    out.extend("| " + " | ".join(row) + " |" for row in rows)
    return out


def render(stats: dict, *, query: dict | None = None,
           matching_paths: list[str] | None = None) -> str:
    total = stats.get("total", 0)
    lines = ["# Regime audit report", ""]
    lines.append(f"**Total artifacts:** {total}")
    fr = stats.get("floor_ratio")
    if fr is not None:
        lines.append(f"**Floor ratio** (0.1+0.2)/0.3: **{fr:.2f}**")
    if query:
        lines.append(f"**Query:** `{json.dumps(query, sort_keys=True)}`")
    lines.append("")
    lines.append("## By regime")
    lines.append("")
    rows = []
    for r in REGIME_ORDER:
        n = stats.get("by_regime", {}).get(r, 0)
        if n == 0:
            continue
        pct = (n / total * 100) if total else 0
        rows.append([REGIME_LABELS[r], str(n), f"{pct:.1f}%"])
    lines.extend(_table(["Regime", "Count", "%"], rows))
    lines.append("")
    lines.append("## By kind")
    lines.append("")
    by_kind = stats.get("by_kind", {})
    rows = [[k, str(n)] for k, n in sorted(by_kind.items())]
    lines.extend(_table(["Kind", "Count"], rows))
    lines.append("")
    lines.append("## By skill")
    lines.append("")
    by_skill = stats.get("by_skill", {})
    headers = ["Skill"] + [r for r in REGIME_ORDER]
    rows = []
    for skill, counts in sorted(by_skill.items()):
        cells = [skill] + [str(counts.get(r, "")) for r in REGIME_ORDER]
        rows.append(cells)
    lines.extend(_table(headers, rows))
    lines.append("")
    if matching_paths:
        lines.append("## Matching paths")
        lines.append("")
        for p in matching_paths:
            lines.append(f"- `{p}`")
        lines.append("")
    return "\n".join(lines)


def _resolve_bundle(arg: str) -> Path:
    if arg == "--latest":
        bundles = sorted(DEFAULT_BUNDLES_DIR.iterdir(), key=lambda p: p.stat().st_mtime)
        if not bundles:
            raise SystemExit(f"no bundles found in {DEFAULT_BUNDLES_DIR}")
        return bundles[-1]
    p = Path(arg)
    if not p.is_absolute():
        p = REPO_ROOT / p
    return p


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m skills.regime_audit_report.render <bundle-dir|--latest>")
        return 2
    bundle = _resolve_bundle(sys.argv[1])
    if not (bundle / "stats.json").exists():
        print(f"no stats.json in {bundle}")
        return 1
    outcome = json.loads((bundle / "stats.json").read_text(encoding="utf-8"))
    query = outcome.get("query") or None
    md = render(outcome.get("stats", {}),
                query=query,
                matching_paths=outcome.get("matching_paths") if query else None)
    out_path = bundle / "report.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"wrote {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
