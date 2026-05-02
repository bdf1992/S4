# Composition rule — deficit_surface

**Status:** part of design preview [prop_2026-05-01_surface-inventory-and-expectation-check](../README.md). Not yet a graduated 0.3/0.4 composition rule. Final placement (this file standalone alongside the skill, vs merged into [foundations/zero-four.md](../../../foundations/zero-four.md)) is deferred until the rule has accumulated usage data.

## What a deficit_surface is

A deficit_surface is a 3.0 orchestration output that names a single surface (existing artifact) and the gap between its observed state and its expected state. It is *not* a primitive — it is a **composed** record whose every component is already a data point or pointer in the existing chain.

A deficit_surface is emitted when a 3.0 orchestration walks a surface's `expectation_check` data points and finds at least one `verdict=fail`. It composes:

- **observed_role** — read from the surface's `surface_inventory_entry` (`artifact_kind`, `graduation_state`).
- **expected_role** — declared by an artifact_kind's expected-role record (data points produced by an expected-role collector — TBD per artifact_kind in a follow-up proposal).
- **failed_expectations** — pointers to `expectation_check` data points whose verdict is `fail` for this surface.
- **candidate_repairs** — emitted by the 3.0 orchestration as proposed transformations; each repair is a structured record naming what would be added/removed/modified to flip the failed expectations to `pass`.

## Shape

```
{
  "surface_pointer": pointer (kind=surface, target=surface_inventory_entry id),
  "observed_role": {"artifact_kind": str, "graduation_state": str},
  "expected_role": str,
  "failed_expectations": [pointer to expectation_check data point, ...],
  "candidate_repairs": [
    {"kind": str, "target_path": str, "transformation": str, "rationale": str}
  ]
}
```

Note the encoding choice: `surface_pointer` resolves through the `surface` resolver to a `surface_inventory_entry` data point. The pointer being **live** is the existence guarantee; the `failed_expectations` list being **non-empty** is the deficit guarantee. Together they encode "the surface exists AND is deficient" without widening the binary pointer status enum — Foundation 3 guarantee 2 (`live | dangling | unresolved`, no third state) is preserved.

## What it is not

- **Not a foundation.** The three foundations (data-point, collection-program, pointer) plus the [zero-four.md](../../../foundations/zero-four.md) composition rule are bedrock; deficit_surface sits one layer above.
- **Not a pointer status.** A pointer is `live` or `dangling`; deficiency is composed from a live pointer + at least one failed expectation_check, not from a third pointer status.
- **Not a deletion signal.** Deficient presence is a *care* marker — the artifact is preserved, repairs are proposed, and only after a Deficit Candidate is graduated does any source modification occur. (See the `--` deficient-presence framing in §3.5 of the cross-walked doctrine; the lift here strips the marker register and routes the same intent through our existing primitives.)

## Promotion pathway

A deficit_surface emitted by 3.0 orchestration is by default a **Deficit Candidate** (per the §11 candidate-type taxonomy lift). Its graduation requires:

1. Each entry in `failed_expectations` has at least one corresponding entry in `candidate_repairs`.
2. The candidate_repair, if applied, would flip the verdict of the corresponding `expectation_check` from `fail` to `pass`. Verifiable by re-running the expectation_check collector after applying the repair.
3. Operator approval, recorded as a graduation event in [foundations/grading-events.md](../../../foundations/grading-events.md) (or its successor index file).

A graduated Deficit Candidate produces an actual modification to the surface; the underlying `surface_inventory_entry` data point's `graduation_state` updates to reflect the post-repair state.

## Why this composition (and not a new bedrock concept)

The cross-walked doctrine places "existence state" at 0.0 root grammar, with a five-valued enum (`unknown / absent / satisfying / deficient / partial`). Adopting that wholesale would mutate Foundation 3 (binary pointer status) and add a new primitive at the bedrock layer. We refuse that mutation.

Instead, the same intent is generated from existing primitives:

- `unknown` → pointer `last_status=unresolved`
- `absent` → pointer `last_status=dangling` with reason `path_missing`
- `satisfying` → pointer `last_status=live` AND every applicable `expectation_check` returns `pass`
- `deficient` → pointer `last_status=live` AND at least one applicable `expectation_check` returns `fail`
- `partial` → derived from the count/distribution of `expectation_check` verdicts; not a primitive

Every state the doctrine names is computable from current primitives plus the `surface_inventory_entry` + `expectation_check` data point kinds this proposal introduces. No bedrock mutation required, no new primitive declared, the binary pointer guarantee preserved. This is the recursive shape from [CLAUDE.md](../../../CLAUDE.md): "even the rules the bedrock uses to fence itself are fenced by the same primitives."
