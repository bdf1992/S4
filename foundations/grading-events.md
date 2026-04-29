# Foundation grading events — log

This file is the explicit log CLAUDE.md requires for any change to a hardcoded foundation. Per [CLAUDE.md](../CLAUDE.md):

> Once committed, treat them as immutable for the duration of this experiment. If you want to change one, that itself is a 0.4 grading event — log it explicitly, do not silently revise.

A 0.4 grading event is recorded here when evidence accumulates that one or more foundations need to change. **The foundations themselves are not modified by this file.** Each event is queued against a foundation; the operator decides whether to approve the proposed change before any foundation file is touched. The change, if approved, is then made in a separate, clearly-attributed commit referencing the event number from this log.

This file is itself **not a foundation** — it is the changelog *adjacent to* the foundations. It is mutable; it accretes one entry per grading event over the life of the experiment.

---

## Event 001 — bedrock not anchored to external standards (PENDING)

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

**Status:** PENDING — no foundation file has been modified. This event is queued. The operator must approve before any of the proposed changes are made.

**If approved**, the work is staged as a sequence:
- (a) Commit a `pyproject.toml` and install pydantic/radon (pre-req).
- (b) Refactor `lib/data_point.py` to construct PROV-JSON-conformant records; refactor `lib/audit.py` to consult radon. Re-run verify; ensure clean.
- (c) Refactor `foundations/data-point.md`, `collection-program.md`, `zero-four.md` to cite the standards in (a) and (b). One commit per foundation. Reference this event number (Event 001) in each commit message.
- (d) Re-run verify against all bundles; regenerate any data points whose provenance shape changed.
- (e) Update [skills/leash_for_hooks/SKILL.md](../skills/leash_for_hooks/SKILL.md) bedrock-pointer table to reference the new shapes.
- (f) Mark this event RESOLVED with the commit SHAs in the resolution block.

**Resolution:** *(not yet resolved)*

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
