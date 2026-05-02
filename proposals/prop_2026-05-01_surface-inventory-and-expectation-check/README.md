# surface_inventory + expectation_check + deficit_surface

**Status:** proposed. Foundation-2 pre-verification has run with overall_verdict=`pass`. Awaiting operator decision recorded against [proposal.json](proposal.json).

## Stakes

**If approved and graduated**, this lands a small unified inventory primitive that:
- Names every artifact in the repo as a structured data point — `(path, artifact_kind, graduation_state, declared_expectation_kinds)`.
- Generalizes the existing per-skill `bundle_self_check` pattern under a domain-neutral name (`expectation_check` family).
- Makes the **deficit surface** composition explicit — `(live surface pointer + failed expectation_check data points + proposed repairs)` — as a sub-4.0 candidate output that documents what needs repair, without inventing a new bedrock layer.

**If rejected**, the existing [skills/gap_audit/collectors/surface_handwalk_recurrence.py](../../skills/gap_audit/collectors/surface_handwalk_recurrence.py) and per-skill `bundle_self_check` infrastructure continue unchanged. The 24 `surface_inventory_absence` gap data points already collected at [skills/gap_audit/datasets/2026-05-01/surface_inventory_absence.jsonl](../../skills/gap_audit/datasets/2026-05-01/surface_inventory_absence.jsonl) remain live and will continue to grow with each new verifier or gap collector that enumerates inline.

**Connections.** Three concurrent in-conversation lifts (from a cross-walk of the protocol-governed-agentic-coding doctrine into our register) compose with this:
- §5 + §6 three-axis posture record (leash × capability × posture) consumes `surface_inventory_entry` data points to scope which surfaces a posture applies to.
- §10.5 shadow / canary / emergency-predicate rollout discipline reads `graduation_state` to know which surfaces are at which phase.
- §11 candidate-type taxonomy: a `Deficit Candidate` cites a `surface_inventory_entry` pointer plus failed `expectation_check` data points as its evidence.

None of those need to land before this graduates. They consume what this emits.

## The measured gap

The companion gap collector [skills/gap_audit/collectors/surface_inventory_absence.py](../../skills/gap_audit/collectors/surface_inventory_absence.py) (added concurrently with this proposal) walks `skills/*/verify.py`, `proposals/*/candidate/*_verifier.py`, and other gap collectors in `skills/gap_audit/collectors/*.py`. It emits one data point per inline surface-scope declaration: top-level `SKILL_REL` / `INPUTS` / `PY_FILES` / `DATASET_FILES` constants, and top-level `_walk` / `_walk_corpus` / `_verifier_files` functions.

At source_state `sha256:4dd60472...` (recorded in [skills/gap_audit/datasets/2026-05-01/surface_inventory_absence.source_state](../../skills/gap_audit/datasets/2026-05-01/surface_inventory_absence.source_state)), the collector emits **24 gap data points across 14 files**:
- 22 of `absence_kind=inline_scope_constant`
- 2 of `absence_kind=inline_walk_function`

Each gap data point names a specific symbol at a specific line in a specific file — places where that file's "what artifacts do I cover" knowledge is hardcoded inline rather than read from a unified inventory. [gap.json](gap.json) cites all 24 as the gap_pointers this proposal closes. Closure: each gap_pointer re-resolves dangling at a future source_state where the cited symbol no longer satisfies its absence_kind (i.e., the file has refactored to read from `surface_inventory_entry` data points).

## What's here

```
candidate/
├── surface_inventory.py     # the collector — 71 substantive lines, audit-budget-conformant
├── value_schema.json        # surface_inventory_entry schema
└── deficit_surface.md       # composition rule documentation (ships with the skill, not a new kind)
gap.json                     # 24 gap_pointers from surface_inventory_absence
pre_verification.json        # Foundation-2 checks: all pass
proposal.json                # the proposal record with full pointer structure
```

`surface_inventory.py` walks `proposals/`, `skills/`, `foundations/`, `meeting-notes/` and emits one `surface_inventory_entry` data point per artifact, with:
- `path` — the artifact's location
- `artifact_kind` — `proposal` / `skill` / `foundation` / `meeting_note` / `other`
- `graduation_state` — `candidate` / `graduated` / `archived` / `unknown` (derived from per-kind rules; e.g., a proposal with non-null `decision_record_pointer` is `graduated`)
- `declared_expectation_kinds` — list of expectation_check kinds that apply to this artifact (e.g., `bundle_self_check`)

Run against current repo state, the candidate emits 30 data points covering 4 proposals, 9 skills, 5 foundations, and meeting-notes. Determinism verified across two runs at the same source_state.

[deficit_surface.md](candidate/deficit_surface.md) documents the composition rule: a deficit surface is a record carrying `{surface_pointer (live), observed_role, expected_role, failed_expectations[], candidate_repairs[]}` — emitted by 3.0 orchestration when a surface's live pointer + its expectation_check data points show one or more failures. This is documentation, not a new graduated kind.

## Pre-verification summary

[pre_verification.json](pre_verification.json) records the Foundation-2 checks. Highlights:

| Check | Verdict | Detail |
|---|---|---|
| audit_budget_under_80 | pass | 71 substantive lines |
| candidate_runs_clean_against_repo | pass | 30 records emitted |
| determinism_runtime_check | pass | byte-identical across two runs |
| no_llm_sdk_imports | pass | imports: `__future__, datetime, hashlib, json, pathlib, typing` |
| no_nondeterminism_imports | pass | datetime used only in collected_at (advisory, per Foundation 1) |
| required_constants_present | pass | COLLECTOR_ID, KIND, VALUE_SCHEMA, INPUTS |
| required_functions_present | pass | collect, verify |

Overall verdict: pass.

## Floor-growth signal

| | Today | After graduation |
|---|---|---|
| Surfaces enumerated explicitly | 0 (implicit per verifier) | 30 (one data point per artifact) |
| Expectation kinds named generically | per-skill (`bundle_self_check` only) | `expectation_check` family (inheritable per artifact_kind) |
| Deficit composition shape | implicit prose | structured 0.3/0.4 record (in candidate/deficit_surface.md) |
| `surface_inventory_absence` count | 24 | trends toward 0 as consumers refactor |

The collector itself is small; leverage comes from giving downstream skills a uniform inventory to join against. This is the SubProtocol "skills floor-growth" pattern: per-leash emission shrinks because the inventory is no longer re-derived inline.

## What is still open after this graduates

This proposal's promotion does **not** automatically close any of the following:

1. **Refactoring consuming files** to read from `surface_inventory_entry` data points instead of inline scope constants. Each refactor is a separate small change that turns one or more `surface_inventory_absence` gap data points dangling.
2. **The §5/§6 posture record** and **§10.5 shadow rollout** lifts — still in conversation, not yet drafted as proposals.
3. **Merging deficit_surface composition into [foundations/zero-four.md](../../foundations/zero-four.md).** This is itself a 4.0 grading event per [foundations/grading-events.md](../../foundations/grading-events.md) and should not happen at this proposal's promotion. The composition rule ships with the skill (Path A in original draft) until the rule has accumulated real usage data showing it earns the bedrock-adjacent placement (Path B).
4. **The `expected_role` declaration per artifact_kind** referenced in the deficit_surface composition. A future small proposal would add a `declared_expectations` collector (or extend this one) so expected_role is data, not authored prose.

## Production placement (post-promotion)

```
skills/surface_inventory/
├── SKILL.md                 # describes the skill's claim and its 0.1 conformance
├── __init__.py
├── lib/                     # vendored data_point + pointer helpers (per each-skill-carries-its-own-lib)
├── surface_inventory.py     # the collector (with .lib imports replacing inline helpers)
├── value_schema.json
├── deficit_surface.md       # composition documentation, skill-local
└── verify.py                # parameterized bundle_verifier shim (pending its own promotion)
```

Inline helpers in the candidate (`_cp`, `_make`) are kept for proposal self-containment per the existing pattern; on promotion they become `from .lib import data_point as dp` and `from .lib import pointer as ptr` to match the convention used by sibling skills.
