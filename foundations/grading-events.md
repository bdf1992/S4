# Foundation grading events — log

This file is the explicit log CLAUDE.md requires for any change to a hardcoded foundation. Per [CLAUDE.md](../CLAUDE.md):

> Once committed, treat them as immutable for the duration of this experiment. If you want to change one, that itself is a 0.4 grading event — log it explicitly, do not silently revise.

A 0.4 grading event is recorded here when evidence accumulates that one or more foundations need to change. **The foundations themselves are not modified by this file.** Each event is queued against a foundation; the operator decides whether to approve the proposed change before any foundation file is touched. The change, if approved, is then made in a separate, clearly-attributed commit referencing the event number from this log.

This file is itself **not a foundation** — it is the changelog *adjacent to* the foundations. It is mutable; it accretes one entry per grading event over the life of the experiment.

---

## Event 001 — bedrock not anchored to external standards (REJECTED 2026-04-29)

**Detected:** 2026-04-29 during operator review of Move 3 output.

**Trigger:** Operator pushback —

> *"I think you need to refactor your architecture to be more in line with the standards that Entropic and partners of Python and stuff like this implement because I don't know if your patterns are standardized and unless you can show me where that is sited I want to second guess your formatting and organization patterns."*

**Investigation (committed, no foundations modified):**

Two research agents were dispatched (claude-code-guide for Anthropic-published specs; general-purpose for external Python / W3C standards). Findings:

| Foundation | What it currently does | Cited standard it should anchor to |
| --- | --- | --- |
| [data-point.md](data-point.md) — `provenance.{collector, source_state, collected_at}` | Authored shape, no citation | **W3C PROV-DM** ([spec](https://www.w3.org/TR/prov-dm/)) — `prov:Entity` / `prov:Activity` / `prov:Agent`; serialize as **PROV-JSON** ([W3C submission](https://www.w3.org/Submission/prov-json/)) — no RDF stack required |
| [data-point.md](data-point.md) — per-kind `value_schema` declared as ad-hoc dicts that nothing validates against | Schema-shaped lies | **JSON Schema Draft 2020-12** ([spec](https://json-schema.org/specification)) authored via **Pydantic v2** ([docs](https://docs.pydantic.dev/latest/)) and exported via `model_json_schema()` |
| [collection-program.md](collection-program.md) — "audit budget ≤ 80 substantive lines" | Pure invention | **Cyclomatic complexity ≤ 10** (McCabe 1976, [DOI](https://doi.org/10.1109/TSE.1976.233837); NIST SP 500-235; Pylint/Ruff/Radon defaults). Replace LOC budget with `radon` / `mccabe` / `ruff C901` enforcement at audit time |
| [zero-four.md](zero-four.md) — orchestration audit budget ≤ 150 LOC | Pure invention | Same: cyclomatic complexity, max-statements ≤ 50 (Pylint default), max-module-lines ≤ 1000 (Pylint default) |

**Proposed changes (NOT YET APPLIED — awaits operator approval):**

1. **`data-point.md`** — replace the bespoke `provenance` shape with a PROV-DM-conformant mapping: emit each data point as a `prov:Entity` with `prov:wasGeneratedBy` an `Activity`, `prov:used` a source-snapshot `Entity`, `prov:wasAssociatedWith` a `SoftwareAgent` (the collector). Keep the rest of the shape (id, kind, value, witness) unchanged. Serialize as PROV-JSON inside the existing record.
2. **`data-point.md`** — value_schemas are declared as Pydantic v2 models in `lib/schemas.py`; the per-data-point `value` is validated against the model on emit; the model's `.model_json_schema()` output is committed as the cross-language contract.
3. **`collection-program.md`** — drop the LOC budget; replace with cyclomatic complexity ≤ 10 (per-function), max-statements ≤ 50 (per-function), max-module-lines ≤ 1000 (per-file). Audit enforcement: `lib/audit.py` consults the `radon` library (or `mccabe` / `ruff` config) instead of counting substantive lines.
4. **`zero-four.md`** — the orchestration budget likewise replaced with cyclomatic complexity rules; verify.py budget removed entirely (it is itself a collector and inherits the same rule).
5. **Project layout** — add `pyproject.toml` at repo root declaring dependencies (`pydantic>=2`, `radon`, `prov` optional), per [PEP 518](https://peps.python.org/pep-0518/) / [PEP 621](https://peps.python.org/pep-0621/). Skill stays flat; no per-skill pyproject.toml ([PyPA discussion](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)).

**Why this is a 0.4 grading event and not a routine refactor:**

The foundations are the bedrock everything leans on. Their shape is the load-bearing claim of the experiment. Changing them mid-experiment is exactly what CLAUDE.md says must be logged, not silently revised. The shape change is also non-trivial: every existing collector, dataset, and verify-pass would need to re-emit / re-derive against the new foundation shape. That work is real, and the operator should decide whether the grounding is worth the migration cost before the migration begins.

**Status:** REJECTED 2026-04-29 — see Resolution below. The four foundation files were stamped with an un-grounding disclosure block in the same commit as this status change. No foundation shape was modified; the bedrock remains as authored.

**Two execution branches (operator picks one):**

### Plan A — APPROVE: execute the foundation grounding

Sequence (8–10 commits, ~4–6h of agent work, medium-high risk because every collector is touched):

| # | Action | Commit |
| --- | --- | --- |
| A.1 | Create `pyproject.toml` at repo root per [PEP 518](https://peps.python.org/pep-0518/) + [PEP 621](https://peps.python.org/pep-0621/). Declare deps `pydantic>=2`, `radon`, `prov` (optional). Run `pip install -e .` once. | `event-001/a1: pyproject.toml + deps` |
| A.2 | New file `skills/leash_for_hooks/lib/schemas.py` — Pydantic v2 models for each KIND (`LlmSdkDenylistEntry`, `HookEventDecl`, `HookConfig`, `ExemplarBundleState`, `BundleSelfCheck`). Export each as `<KIND>_SCHEMA = Model.model_json_schema()` for collectors to import. | `event-001/a2: pydantic schemas + JSON Schema exports` |
| A.3 | Refactor `lib/data_point.py` — `make_data_point` constructs PROV-JSON record (`prov:Entity` for the data point + source snapshot, `prov:Activity` for the run, `prov:SoftwareAgent` for the collector, relations `wasGeneratedBy` / `used` / `wasAssociatedWith`). Replace `provenance` field with `prov` field carrying the PROV-JSON object. Validate `value` against the per-KIND Pydantic model on emit. | `event-001/a3: PROV-DM provenance + Pydantic value validation` |
| A.4 | Refactor `lib/audit.py` — replace `_substantive_line_count` with `radon.complexity.cc_visit` and `radon.metrics.mi_visit`. New thresholds: `MAX_CC = 10`, `MAX_STATEMENTS = 50`, `MAX_MODULE_LINES = 1000`. Cite McCabe 1976 (DOI 10.1109/TSE.1976.233837), NIST SP 500-235, Pylint defaults in module docstring. | `event-001/a4: cyclomatic-complexity audit (radon)` |
| A.5 | Adopt the new `make_data_point` signature in each of the 4 collectors. Drop their per-collector schema dicts (now imported from `lib/schemas.py`). Run each collector; confirm output validates. | `event-001/a5: collectors adopt new schemas + provenance` |
| A.6 | Rewrite `foundations/data-point.md` to cite W3C PROV-DM (https://www.w3.org/TR/prov-dm/), PROV-JSON (https://www.w3.org/Submission/prov-json/), JSON Schema 2020-12 (https://json-schema.org/specification), Pydantic v2 (https://docs.pydantic.dev/latest/). Reference Event 001 in the file header. | `event-001/a6: foundation data-point.md cites PROV + JSON Schema` |
| A.7 | Rewrite `foundations/collection-program.md` to cite cyclomatic-complexity standards (McCabe / NIST / Pylint defaults / Ruff C901 / Radon ranks). Reference Event 001. | `event-001/a7: foundation collection-program.md cites complexity stds` |
| A.8 | Rewrite `foundations/zero-four.md` orchestration-budget rule to cite the same. Reference Event 001. | `event-001/a8: foundation zero-four.md cites complexity stds` |
| A.9 | Re-run verify against the skill bundle and the most recent output bundle. Regenerate stale datasets if provenance shape moved. | `event-001/a9: regenerate datasets, verify clean` |
| A.10 | Update `skills/leash_for_hooks/SKILL.md` bedrock-pointer table and recursion-seam.md (if shapes changed). Mark Event 001 RESOLVED in this file with all commit SHAs. | `event-001/a10: SKILL.md + RESOLVED` |

**Approval phrase:** "Plan A approved" or "execute Event 001 Plan A".

### Plan B — REJECT: close out as not-worth-the-migration-cost

Sequence (1 commit, ~30min, zero risk — paperwork only):

| # | Action | Commit |
| --- | --- | --- |
| B.1 | Add a one-paragraph "Un-grounding disclosure" block to the top of each of the four foundation files: *"This foundation is hardcoded from CLAUDE.md without external citation. Event 001 documented the gap and was rejected on YYYY-MM-DD per operator decision; the bedrock remains as authored. See [grading-events.md Event 001](grading-events.md) for the rejected proposal and re-trigger conditions."* | `event-001/b1: foundations carry un-grounding disclosure; Event 001 REJECTED` |

Plus mark this event REJECTED with the operator's rationale and the file SHAs of the disclosure-stamped foundations.

**Re-trigger conditions to log when rejecting** (so a future session knows when to re-open the event):
- A sibling leash for a non-Claude-Code surface needs the data-point provenance to be portable across machines / tools — un-grounded shape will fail.
- An external collaborator wants to consume the data points emitted by this experiment — they cannot do so without a published schema.
- Audit budget LOC count starts producing false positives or false negatives that complexity would catch correctly.
- Any of the foundations needs to change for any other reason — fold the grounding refactor into that change rather than doing two grading events.

**Approval phrase:** "Plan B" or "reject Event 001".

### Refining the plan

Either branch can be edited before execution. Common refinements:

- "Plan A but skip the cyclomatic-complexity refactor" — drops A.4, A.7; keep PROV + Pydantic.
- "Plan A but do PROV only" — drops A.2, A.4, A.7; keep PROV + the existing audit.
- "Plan A but use jsonschema instead of Pydantic" — A.2 emits raw JSON Schema dicts, A.3 validates with `jsonschema.validate`. Lighter dep weight; loses IDE typing.

**Resolution (2026-04-29):** REJECTED per operator decision (Plan B). Rationale: the operator had already begun an in-flight sibling leash at `skills/leash_for_slash_commands/` in the same session. A 4–6h foundation grounding refactor (Plan A) would have frozen that sibling work mid-stream and forced re-validation of every collector against shifting bedrock, with no corresponding 0.2 signal indicating the grounding is operationally needed yet. Floor-growth across rounds — sibling leashes reusing shared bedrock — is the experiment's named success metric (per [CLAUDE.md](../CLAUDE.md)); deferring the grounding preserves momentum on that metric. Plan B was executed in a single commit: each of the four foundation files now carries an un-grounding disclosure block (after the `**Status:**` line, before the first content section) pointing back here. Re-trigger conditions are listed under Plan B above; revisit when one fires.

---

**Handoff document for fresh-Claude:** [meeting-notes/2026-04-29-handoff-event-001-decision.md](../meeting-notes/2026-04-29-handoff-event-001-decision.md) — read on session start to orient.

---

## Event 002 — vocabulary lift to two-axis (programs vs protocols) framing (IN PROGRESS 2026-05-01)

**Detected:** 2026-05-01 during operator-driven CLAUDE.md vocabulary clarification session.

**Trigger:** Operator surfaced that the work to date had been confused between *what we are making* (X.0 programs) and *the discipline by which we make them* (0.X protocols), and clarified the two-axis split:

- **Programs (X.0)** — 1.0 handwritten code, 2.0 learned models, 3.0 prompted agents, 4.0 coupled-system. The program kinds Karpathy named, plus the one this experiment is producing.
- **Protocols (0.X)** — 0.1 the discipline for 1.0, 0.2 for 2.0, 0.3 for 3.0, 0.4 the shared protocol for 4.0.
- **0.0** — the candidate state of any X.0 program before its 0.X protocol has graduated it.

CLAUDE.md was updated under direct operator authorization in the same session. The operator then explicitly directed lifting this framing throughout the rest of the repo, including the foundations.

**Investigation:** The pre-lift wording across the four foundations conflated programs with protocols:

- **data-point.md** — uses "rung" loosely to mean "layer in the chain"; "0.1 contract assertion / 0.2 model input / 0.3 plan justification" naming conflates protocol with the program produced under it.
- **collection-program.md** — references "0.2 datasets" (should be: 2.0 signals trained on 1.0-computed datasets, all under 0.2 protocol); uses "ladder collapse" framing.
- **pointer.md** — uses "rung" / "ladder" / "0.X plan step" throughout; pointer kinds like `data_point` / `collector` / `signal` map cleanly to the new framing without rename.
- **zero-four.md** — most affected. Names the bundle a "0.4 bundle" (should be: 4.0 bundle); names components "0.1 layer / 0.2 layer / 0.3 layer" (should be: 1.0 / 2.0 / 3.0 components produced under their protocols); inter-layer rules titled "0.0 → 0.1", "0.1 → 0.2", etc., where the right read is "candidate-X.0 → graduated-X.0 via 0.X protocol".
- **proposal.md** — describes a proposal as a "candidate 0.1 asset" (should be: candidate-1.0 collector, i.e. a 0.0-stage applicant for the 1.0 floor under 0.1 protocol).

**Proposed change:** Vocabulary lift across all foundation files. **Substantive shapes are unchanged**: the data-point record fields, the collector validity constraints, the pointer protocol, the 4.0 bundle composition rule, the proposal contract — all unchanged at the shape/guarantee/validation level. Only the language is updated to use the two-axis framing established in [CLAUDE.md](../CLAUDE.md). No re-derivation of any data point, collector, dataset, or signal is required by this change.

**Why this is a 4.0 grading event:** Even though the lift is renaming-only and the shapes are preserved, the bedrock rule per CLAUDE.md is that *any* change to a foundation must be logged, not silently revised. The four foundation `.md` files ARE the bedrock; their text is load-bearing. Logging Event 002 here makes the change traceable instead of silent.

**Status:** IN PROGRESS — applied 2026-05-01 in the same commit cycle as the CLAUDE.md update, by direct operator authorization.

**Resolution:** Pending — commit SHAs to be recorded once lift is applied. Re-affirms Event 001's rejection: the un-grounding disclosure blocks remain in place; this lift does not anchor the bedrock to external standards (PROV-DM, JSON Schema, McCabe complexity) — it only renames within the existing un-grounded shape.

---

## Event 003 — independent validation and non-blocking production (IN PROGRESS 2026-05-02)

**Detected:** 2026-05-02 during operator correction of the running protocol.

**Trigger:** Operator clarified that the repo should not block useful work on repeated validation of lower layers:

> "I want to validate 0.4 and 4.0 ... I don't need to validate 0.1 and 0.2 as long as there are files validating them ... I only need to validate what is produced ... I want to edit this repo to act in such a way that I do not block work."

**Investigation:** The current text already allowed `not_ready` emission-readiness to produce a `candidate` instead of failing, but CLAUDE.md still said to stop after early move checkpoints and zero-four.md described inline re-validation of collectors, datasets, and signals inside every bundle walk. That made lower-layer proof work act like a synchronous gate instead of an independent proof surface.

**Proposed changes:**

1. **CLAUDE.md** — add an explicit validation-scope rule: once 0.1/0.2 validator or receipt files exist, later work may point at them and continue; blocking validation belongs to the produced 0.3/3.0 artifact and final 0.4/4.0 bundle claim.
2. **CLAUDE.md** — rewrite "Stop and report" as "report validation state and continue with the next non-destructive work item" except for destructive operations, unlogged foundation mutation, or explicit operator decisions.
3. **zero-four.md** — update the grading procedure so the 0.4 walker consumes lower-layer validation receipts, refreshes them only when absent or stale, and downgrades to `candidate` when a dependent receipt is missing/stale instead of blocking unrelated production.
4. **zero-four.md** — update negative definitions and the 3.0 -> 4.0 gate to distinguish "cannot claim 4.0 yet" from "must stop work."

**Status:** IN PROGRESS — applied 2026-05-02 by direct operator authorization.

**Resolution:** Pending — commit SHAs to be recorded once this change set is committed. The intended behavior after this event is: produce the work, preserve validation receipts for lower layers, and let the final walker assign the strongest honest claim (`candidate` or `4.0`) without freezing unrelated substrate growth.

---

## Event template

For future events, copy this skeleton:

```
## Event NNN — <one-line summary> (<PENDING|RESOLVED>)

**Detected:** <date>, <by whom / from what>.
**Trigger:** <quote or pointer to the source>.
**Investigation:** <what was checked, with cites>.
**Proposed changes:** <enumerated, per-foundation>.
**Status:** <PENDING | APPROVED | RESOLVED>.
**Resolution:** <commit SHAs and notes when resolved>.
```
