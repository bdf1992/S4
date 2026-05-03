"""Composite grounding rendering for the /cook skill.

Surfaced into [.claude/skills/cook/SKILL.md] at invocation time so each
cook session reads two lenses on the floor before picking a target:

  - 1.0 lens (peer consumption per skill, via tools.floor_growth)
  - 2.0 lens (regime distribution, via the regime_distribution signal
    fitted on regime_classification's data points)

Importing skills.regime_audit.signals.regime_distribution at module
top — and calling fit() on freshly-collected regime_classification
rows — is the load-bearing wiring this file is for: it converts
regime_audit from candidate_signal_unfenced (no peer consumes its
signals/) to graduated under floor_growth's classifier. Removing the
import would unwire that fence and the next floor_growth run would
flag it.

Run:
  python -m tools.cook_grounding         # composite grounding summary
"""
from __future__ import annotations

import sys

from skills.regime_audit.collectors import regime_classification
from skills.regime_audit.signals import regime_distribution
from tools import floor_growth

REGIME_ORDER = ("bedrock", "0.0", "0.1", "0.2", "0.3", "unclassified")


def _render_distribution(fitted: dict) -> list[str]:
    out = ["## Floor distribution — regime_distribution signal fitted on current source", ""]
    fr = fitted.get("floor_ratio")
    if fr is None:
        out.append("`floor_ratio (0.1+0.2)/0.3`: **undefined** (no 0.3 artifacts in corpus)")
    else:
        out.append(f"`floor_ratio (0.1+0.2)/0.3`: **{fr:.2f}** "
                   f"(success metric named in [CLAUDE.md](../CLAUDE.md))")
    out.append(f"total artifacts walked: {fitted['total']}")
    out.append("")
    out.append("by regime:")
    out.append("")
    out.append("| regime | count |")
    out.append("| --- | --: |")
    for r in REGIME_ORDER:
        n = fitted["by_regime"].get(r, 0)
        out.append(f"| `{r}` | {n} |")
    out.append("")
    return out


def _render_substrate_x_status(fitted: dict, fg_points: list[dict]) -> list[str]:
    fg_by_skill = {p["value"]["skill_name"]: p["value"] for p in fg_points}
    by_skill_regime = fitted["by_skill"]
    skill_names = sorted(set(fg_by_skill) | {k for k in by_skill_regime if not k.startswith("_")})

    out = ["## Per-skill substrate × peer status", ""]
    out.append("0.1/0.2/0.3 columns: artifact counts per regime under that skill, from the regime_distribution fit.")
    out.append("status / signals_consumed: from the floor_growth peer-consumption walk.")
    out.append("")
    out.append("| Skill | 0.1 | 0.2 | 0.3 | status | signals_consumed |")
    out.append("| --- | --: | --: | --: | --- | :-: |")
    for sk in skill_names:
        ra = by_skill_regime.get(sk, {})
        fg = fg_by_skill.get(sk, {})
        status = fg.get("status", "—")
        consumed = "yes" if fg.get("signals_consumed") else ("—" if not fg else "no")
        out.append(
            f"| `{sk}` | {ra.get('0.1', 0)} | {ra.get('0.2', 0)} | {ra.get('0.3', 0)} | "
            f"**{status}** | {consumed} |"
        )
    out.append("")
    return out


def render() -> str:
    ss_regime = regime_classification.compute_source_state()
    rows = regime_classification.collect(ss_regime)
    fitted = regime_distribution.fit(rows)

    ss_floor = floor_growth.compute_source_state()
    fg_points = floor_growth.collect(ss_floor)

    lines = ["# Cook grounding — composite (floor-growth × regime-distribution)", ""]
    lines += _render_distribution(fitted)
    lines += _render_substrate_x_status(fitted, fg_points)
    lines.append("---")
    lines.append("")
    lines.append(f"_regime_classification source_state_: `{ss_regime[:32]}…`  ")
    lines.append(f"_floor_growth source_state_: `{ss_floor[:32]}…`")
    return "\n".join(lines)


def main() -> int:
    print(render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
