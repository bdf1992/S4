# Debt record schema

A **debt record** is a structured, mutable artifact that names an honest gap in the system: an authored shape that should be grounded, a working-but-misshapen component, an ad-hoc convention that should be a real validator, a known surface-specific bug, etc. Debts are first-class because gaps are a permanent feature of any real system; treating them as commentary instead of structured records lets them rot or get rediscovered.

This artifact is **agent-native and standalone** (per [memory/feedback_artifact_skill_split.md](../../../.claude/projects/c--Users-bdf19-Desktop-zero-four-experiment/memory/feedback_artifact_skill_split.md)) — any agent can read, validate, query, and update these JSON files without UI assumptions. Human-facing renders (status boards, reports, debt summaries) belong in separate render skills that walk this directory.

## File layout

- One JSON file per debt: `D-NNN.json`, where `NNN` is a zero-padded sequential ID.
- IDs are append-only — never reused, never renumbered.
- Mutability: a debt's *content* (kind, principal, interest, payoff) is set at creation and only edited to correct errors; its *status* and *last_updated_at* are mutable as the debt's lifecycle progresses.

## Fields

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | yes | `D-NNN` |
| `subject` | string | yes | path or component name the debt is about (e.g., `lib/data_point.py`, `provenance shape`, `audit budget rule`) |
| `kind` | enum | yes | one of `authored_not_grounded`, `surface_specific_bug`, `ad_hoc_shape_no_validator`, `missing_tool`, `working_but_unanchored` |
| `principal` | string | yes | the gap itself, in prose. What's owed. |
| `interest` | string | yes | the ongoing cost of carrying the debt. What it costs us NOT to fix this. |
| `payoff` | string | yes | what closes the debt: a citation URL, a refactor description, a standard to adopt. |
| `severity` | enum | yes | `load_bearing`, `cosmetic`, `unknown` |
| `status` | enum | yes | `open`, `parked`, `closed_paid`, `closed_written_off`, `superseded` |
| `re_trigger` | string | yes | a condition that should reopen this debt if it's parked or written off (e.g., "second consumer of bedrock appears", "operator wants scoped state on slash leash") |
| `created_at` | string (ISO 8601 date) | yes | YYYY-MM-DD |
| `last_updated_at` | string (ISO 8601 date) | yes | YYYY-MM-DD |
| `closure` | object | iff status starts with `closed_` or is `superseded` | `{evidence: string, closed_at: YYYY-MM-DD}`. Evidence is a commit SHA, citation URL, or short prose explanation. |
| `supersedes` | string | iff status is `superseded` | the `id` of the debt that supersedes this one |
| `depends_on` | list of strings | optional | other debt ids that must close before this one can close (e.g., D-001 depends_on D-004 because PROV-DM refactor needs Pydantic / prov deps that arrive with pyproject.toml). Renderers may show this as edges. |

## Status semantics

- **open** — actively unresolved; the gap exists and is being carried.
- **parked** — known but not currently being worked; the re_trigger names what would move it back to open.
- **closed_paid** — resolved by grounding/refactor/standard adoption. `closure.evidence` cites what closed it.
- **closed_written_off** — resolved by deciding to accept the gap as the cost we're choosing. `closure.evidence` is prose justifying acceptance.
- **superseded** — replaced by a different debt that more accurately frames the gap. `supersedes` points at the replacement.

## Validation

[validate.py](validate.py) walks `debts/D-*.json`, applies the schema, and reports violations. Run as `python -m debts.validate` from repo root. Exit 0 iff every record validates.

## What a debt record is *not*

- Not a foundation. Foundations are immutable specs ([foundations/](../foundations/)). Debts are mutable status artifacts.
- Not a 0.4 grading event. Grading events are foundation-change moments ([foundations/grading-events.md](../foundations/grading-events.md)). Debts are persistent gap-registry entries that may or may not motivate a future grading event.
- Not a 0.1 data point. Data points are *measurements* with provenance walking real source. Debts are *claims* about the system's epistemic state. Different category.
- Not a TODO or comment. Those rot. A debt's structured fields force the gap to be statable in terms a verifier can walk.

## Promotion path

If this artifact earns its keep — used by both leashes, and the operator references it during gap-handling — promotion to **Foundation 5** in a logged grading event is the natural next move. Until then it is a sub-foundation primitive that the existing foundations do not depend on.
