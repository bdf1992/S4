# Override record — leash-for-symphony bundle built before seam-gate fires

**Date:** 2026-04-30
**Operator:** repo owner (single-operator experiment)
**Override target:** [skills/leash_for_hooks/recursion-seam.md §"When the seam fires (the operator-side gate)"](../../skills/leash_for_hooks/recursion-seam.md#L9), specifically **outcome 5** — the rule that a sibling leash for a new surface gets built only after *repeated* hand-walks against that surface accumulate as a measured signal.
**Override path:** [README.md §"Two paths for the operator" — Path B](README.md#two-paths-for-the-operator).

## What the gate says, and why it is being overridden

Recursion-seam outcome 5: *"the operator is repeatedly applying chain discipline by hand to a surface no existing leash covers. Every time the same shape of ad-hoc verification gets re-derived, that recurrence is the signal that a new leash should formalize it."*

The signal that would justify outcome 5 firing for `surface=symphony` is "the operator has hand-walked Symphony chain discipline N times across N sessions." As of this commit, that signal cannot fire, for two distinct reasons:

1. **No collector exists yet that measures it.** A `surface_handwalk_recurrence` collector under [skills/gap_audit/](../../skills/gap_audit/) (or a successor) would be required to walk session history, meeting notes, and proposals for repeated ad-hoc Symphony chain-discipline application. That collector is not built.
2. **Even if built, the corpus is degenerate.** Symphony was first named in this session, on this date. There are zero prior occurrences for the collector to count.

The override decision: *Path A* (build the collector first, wait for the corpus to accumulate naturally) treats Symphony as ordinary surface-discovery — which it is not. Symphony is a structurally novel surface (first non-Claude-Code target; SPEC §10.5 already declares the leash as an explicit slot the implementation must fill), and chain-discipline-by-hand against it cannot accumulate without first having the formalization. The seam-gate's outcome-5 logic is correctly shaped for surfaces *operators are already touching ad-hoc* — it is not the right shape for *novel surfaces the operator has just decided to touch*.

This is itself a 4.0 grading event on the seam doc — the rule is correctly shaped for one case (sweep up existing hand-walks) and incorrectly shaped for another (formalize-before-touching for a novel external surface). Logging this override loudly is what "vocal mode" looks like applied to the apparatus's own discipline: rather than silently ignoring the gate, record exactly what was done and why so the next operator (or a future audit) can see the override and judge it.

## What this override authorizes

Building [skills/leash_for_symphony/](../../skills/leash_for_symphony/) as a v0 skill bundle with:

- `leash_state.json = {"state": "off", "vocal": true}` — the operator's chosen toggle for this surface, per the [proposal README](README.md).
- Full skill skeleton (collectors, signals, orchestrate, verify) targeting [`hawkymisc/cc-symphony`](https://github.com/hawkymisc/cc-symphony)'s `WORKFLOW.md` shape as the candidate artifact.
- `claim` field in emitted bundles **must remain `"candidate"`** until the corpus reaches `MIN_EXEMPLARS`. No bundle is allowed to claim `"4.0"` as a side effect of this override. The override authorizes *existence*, not *promotion*.

## What this override does NOT authorize

- It does **not** modify recursion-seam.md. The seam doc remains as-is; this override is logged as a per-instance exception, not a doctrinal revision. Future surfaces still flow through the gate by default.
- It does **not** modify any of the three foundations. Foundation 1, 2, 3 are immutable for the duration of the experiment per CLAUDE.md.
- It does **not** authorize promotion of any emitted bundle to `4.0`. That still requires `emission_readiness` firing `ready` against a real exemplar corpus.
- It does **not** authorize integration with Symphony at runtime. The skill produces a `WORKFLOW.md` proposal; it does not push, deploy, or invoke any Symphony runtime.

## Followup that would close the override

If, in a later round, the seam doc is amended to handle "novel-surface-formalize-before-touch" as a distinct outcome (call it outcome 6), this override record can be retired and the leash-for-symphony skill becomes a normal seam-conformant emission. Until then, this record is the audit trail.

## Pointers

- [README.md](README.md) — the proposal this override accompanies.
- [skills/leash_for_hooks/recursion-seam.md](../../skills/leash_for_hooks/recursion-seam.md) — the gate being overridden.
- [foundations/grading-events.md](../../foundations/grading-events.md) — the framework this override fits under.
- [skills/leash_for_symphony/](../../skills/leash_for_symphony/) — the apparatus this override authorizes (created in the same commit set as this record).
