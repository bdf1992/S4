# Foundation 2 — Collection-program shape

**Status:** hardcoded after Move 1 commit. Immutable for the rest of this experiment. Any change to this file is itself a 0.4 grading event and must be logged explicitly, not silently revised.

---

> **Un-grounding disclosure (Event 001 rejected, 2026-04-29).** This foundation is hardcoded from [CLAUDE.md](../CLAUDE.md) without external-standard citation. Event 001 documented the gap (in particular the "audit budget ≤ 80 substantive lines" rule was authored, not anchored against McCabe cyclomatic complexity, NIST SP 500-235, or Pylint/Ruff/Radon defaults) and was **rejected** per operator decision: the 4–6h migration would have frozen in-flight sibling-leash work without a corresponding 0.2 signal that the grounding is needed yet. The bedrock remains as authored. See [grading-events.md Event 001](grading-events.md) for the rejected proposal and re-trigger conditions.

---

## What a collection program is

A collection program is a deterministic, auditable, no-LLM program whose only purpose is to walk a declared region of source and emit data points (Foundation 1). It is the only thing in this experiment that is allowed to *make* a data point. Nothing else can.

A collection program is small on purpose. The smallness is load-bearing: it is what makes the program un-second-guessable. A long, opaque, or branching collector can be quietly rewritten to change the answer without anyone noticing. A short, single-purpose collector cannot.

## Shape

A collection program is a single source file (Python, for this experiment, until a domain demands otherwise) that satisfies all of the following:

| Property | Constraint |
| --- | --- |
| `collector_id` | Declared as a top-level constant. Stable string, used in every data point's `id` prefix. Changing it invalidates all data points it ever produced. |
| `kind` | Declared as a top-level constant. Names exactly one data-point kind this collector emits. One collector → one kind. |
| `value_schema` | Declared as a top-level constant or as an importable schema artifact. Specifies the shape of `value` for this `kind`. |
| `inputs` | Declared as a top-level constant: the list of source paths or source patterns the collector is allowed to read. Reading anything outside this list is a violation. |
| `collect(source_state)` | The single entry point. Takes a source-state identifier (e.g. a git SHA or working-tree hash), reads only `inputs` at that state, returns a list of data points. |
| `verify(data_point)` | The verification entry point. Takes a recorded data point, re-walks its declared inputs at its `provenance.source_state`, and returns `("live", evidence)` or `("dangling", reason)`. |
| Audit budget | The whole file is at most one screenful of substantive code (target: ≤ 80 lines excluding imports, schema, and tests). A collector that grows past this is split or refused. |
| No LLM | The file imports no language-model SDK and makes no model API call, directly or transitively. The full transitive import set is checkable. |
| No nondeterminism | The file does not import or use `random`, `time`, `datetime` (except to record `collected_at`, never to influence `value`), `uuid`, network sockets, environment variables that vary across runs, or any source of nondeterminism. |
| Pure read | The file does not write to source. It may write to a data-point store, and only there. |

A program failing any one of these is not a collector. It can call itself one; the validator rejects it.

## Guarantees a valid collector provides

1. **Determinism.** `collect(s)` returns byte-identical output across runs for the same `s` and the same source contents at `s`. There is no path through the program that is influenced by the wall clock, randomness, network state, or any model.
2. **Source-walk only.** Every byte the collector reads comes from `inputs` at `source_state`. Nothing else is consulted; nothing else can change the answer.
3. **Single-kind output.** Every data point emitted has the declared `kind` and a `value` matching `value_schema`. Mixed-kind output is a violation.
4. **Auditability.** A reader can hold the entire program in their head in one sitting. No clever indirection, no plugin layer, no dynamic dispatch chosen at runtime.
5. **Self-verification.** `verify(dp)` re-walks the same inputs at the recorded source_state and reports live-or-dangling without re-emitting. A collector that cannot verify what it produced is not finished.

## Detectable violations

Each violation MUST be detectable by a 0.1 program. A violation class that requires a human's judgement, or a model's read, indicates a hole in this foundation.

| Violation | How it is detected |
| --- | --- |
| Missing required top-level declaration (`collector_id`, `kind`, `value_schema`, `inputs`, `collect`, `verify`) | Static check: parse the file's AST; confirm the declarations exist. |
| Imports a language-model SDK | Static check: walk the import graph (including transitive); reject if any node matches the LLM-SDK denylist (e.g. `anthropic`, `openai`, `google.generativeai`, `cohere`, etc.). The denylist is itself maintained as a data-point-producing collector so it is auditable, not authored. |
| Uses a banned source of nondeterminism | Static check: AST scan for the banned imports/calls; reject on match. `datetime.now()` and similar may appear only inside the recording of `collected_at`, never inside any branch that influences `value` or `witness`. The check is structural: any `datetime`/`time`/`random` call reachable from `value` or `witness` derivation paths fails the scan. |
| Reads outside declared `inputs` | Runtime check: run the collector under a sandbox that records every file open; diff against `inputs`; reject if any read is outside. |
| Output does not match `value_schema` | Runtime check: validate every emitted data point against `value_schema`; reject the run on first failure. |
| Re-running on identical source state diffs the output | Determinism check: run twice in clean environments; diff outputs byte-for-byte; reject on non-empty diff. |
| File exceeds the audit budget | Static check: line count of substantive code; reject if over budget. The budget can be tightened over time; it cannot be loosened without a 0.4 grading event. |
| `verify(dp)` for a known-live data point returns `dangling` | Self-consistency check: emit a data point, immediately verify it; must be `live`. |

A collector that fails any check is not used. Data points it has already produced are quarantined and re-collected (or invalidated) by a known-good replacement.

## The denylist for "no LLM" is itself a data point

The list of import names that count as "an LLM SDK" cannot be authored as prose inside this file, because then the bedrock would be a sentence. Instead:

- The list lives at a single source path (e.g. `foundations/llm-sdk-denylist.txt`).
- A dedicated collector of `kind = llm_sdk_denylist_entry` walks that file and emits one data point per entry.
- The "no LLM" check on any other collector consults those data points, not the file directly.
- Adding or removing an entry from the denylist is therefore visible as a change in the data-point store, not just a file diff. (The list is a Move 3 build, not a Move 1 build; this foundation only specifies that the check must consume data points, not prose.)

This is the recursive shape the bedrock requires: even the rules the bedrock uses to fence itself are fenced by the same primitives.

## What a collection program is not

- Not an analysis tool. It does not compute insights, summaries, recommendations, or scores. It walks source and reports what is there. Insights belong to 0.2 (signals over collected data) and 0.3 (orchestration over signals), not here.
- Not a transformer. It does not rewrite source, generate code, fill templates, or produce any output that is not a data point.
- Not a model. It has no parameters, no thresholds tuned on data, no learned behavior. A program with thresholds tuned on data is a 0.2 artifact and belongs there, not here.
- Not a wrapper around an LLM. There is no "thin LLM call to extract a number from text." A collector that delegates its judgement to a model is a 0.3 process pretending to be a 0.1 collector.

## Why this shape

Each constraint exists to close a specific failure mode:

- The audit budget closes *quiet rewrite*. A small program's diff is loud; a large program's diff is camouflage.
- The single-kind / declared-inputs / declared-schema constraints close *scope creep*. A collector that does many things eventually does the wrong thing.
- The no-LLM and no-nondeterminism constraints close *bedrock contamination*. The whole experiment leans on the claim that the bottom rung does not lean on a model. A single LLM call in a collector breaks that claim everywhere.
- Self-verification closes *write-only data*. A data point you cannot re-derive is not a measurement; it is a memory.

Holding all of these at once is what makes 0.1 a real floor. The next rung up — 0.2 models trained on what these programs produce — has a chance of meaning what it claims to mean. Without these, the 0.2 datasets are just authored prose with extra steps, and the whole ladder collapses to 0.0.
