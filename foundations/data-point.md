# Foundation 1 — Data-point shape

**Status:** hardcoded after Move 1 commit. Immutable for the rest of this experiment. Any change to this file is itself a 0.4 grading event and must be logged explicitly, not silently revised.

## What a data point is

A data point is the atomic non-LLM unit of evidence in this experiment. Every claim made by any rung — a 0.1 contract assertion, a 0.2 model input, a 0.3 plan justification — bottoms out in one or more data points. If a claim cannot be resolved to data points, it is not evidence; it is prose.

A data point is not authored. It is *computed*, by a collection program (Foundation 2), against real source state, and its identity is fixed by what that program saw.

## Shape

A data point is a record with exactly these fields. A record missing any field, or carrying additional fields not declared here, is not a data point.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | string | yes | Stable handle. Format: `{collector_id}:{content_hash}`. Two data points with the same `id` MUST have the same `value`. |
| `kind` | string | yes | The class of measurement. Each `kind` is declared by exactly one collector. Examples: `file_exists`, `line_count`, `symbol_definition`, `dataset_row`, `pointer_resolution`. |
| `value` | typed-by-kind | yes | The actual measurement. The type and schema of `value` are fixed by `kind`; a data point of kind K whose `value` does not match K's declared schema is malformed. |
| `provenance.collector` | pointer (Foundation 3) | yes | Pointer to the collection program that produced this data point. Pointer kind: `collector`. |
| `provenance.source_state` | string | yes | Identifier of the source state walked. For repo-source collectors: a git commit SHA, or a working-tree content hash. The source_state names what was walked, not when. |
| `provenance.collected_at` | ISO-8601 timestamp | yes | Wall-clock at collection. Advisory only — never load-bearing for verification. Present so a reader can judge how stale a recorded data point is before re-collecting. |
| `witness` | string | yes | Minimal fingerprint that lets a verifier confirm `value` against `provenance.source_state` without re-running the full collector. Typically a hash of the inputs the collector read. May equal `id`'s content_hash when that suffices. |

There is no free-text field. There is no `notes`, no `description`, no `confidence`. If a collector wants to attach extra structured information, it does so by emitting additional data points of additional kinds, never by widening this schema.

## Guarantees a valid data point provides

1. **Re-derivability.** Given the same `provenance.source_state` and the same `provenance.collector`, re-running the collector produces a byte-identical `value` and `witness`. There is no clock, no randomness, no external network state in the path.
2. **Schema-conformance.** The record validates against the table above, and `value` validates against the schema declared by `kind`.
3. **Structural provenance.** `provenance.collector` is a pointer (Foundation 3), not a sentence. A reader can resolve it deterministically and reach the actual collector source.
4. **Source-anchoring.** `provenance.source_state` names a real, addressable state of source the collector walked. It is never `"none"`, `"the conversation"`, `"recent memory"`, or any other non-source anchor.
5. **No-LLM provenance.** No step in the chain that produced this data point invoked a language model. The data point's truth does not depend on a model's output.

A record satisfying all five is a data point. A record failing any one is a candidate that must be rejected by the data-point validator.

## Detectable violations

Each violation below MUST be detectable by a 0.1 program — not by a reader's judgement, not by a model's grade. If a violation class cannot be detected mechanically, this foundation has a hole and must be revised at the next 0.4 grading event.

| Violation | How it is detected |
| --- | --- |
| Missing or extra top-level field | Schema validator rejects the record. |
| `value` does not match the schema declared by `kind` | Per-kind validator rejects the record. |
| `provenance.collector` is prose, not a pointer | Pointer validator (Foundation 3) rejects it; cannot resolve it deterministically. |
| `provenance.source_state` is `null`, empty, or not resolvable to a real source state | Source-state resolver rejects it. |
| Re-running the collector against `provenance.source_state` produces a different `value` or `witness` | Re-derivation check fails; data point is contaminated or collector is nondeterministic. |
| Collector at `provenance.collector` imports an LLM SDK or otherwise calls a model in its execution path | Static check on collector source (grep for known SDKs; AST check for model-call patterns). See Foundation 2 for the canonical check. |
| Two data points share an `id` but differ in `value` | ID-uniqueness check across the data-point store. |
| `witness` does not match the recomputation of the collector's declared input fingerprint | Witness check fails; record was hand-edited or the source moved. |

Detection of any of these MUST result in the data point being rejected — never warned, never tolerated, never patched. A rejected data point is removed from the store; whatever depended on it is now unsupported and must be re-collected or invalidated.

## What a data point is not

- Not a citation. A citation is a sentence in a markdown file that names a source. A data point is a structured record produced by a program. Citations rot; data points either re-derive identically or are rejected.
- Not a confidence claim. A data point has no `confidence` field. Confidence belongs to 0.2 signals, not to 0.1 measurements.
- Not a model output. A 0.2 model's prediction is not a data point. The dataset row that fed into training the model is a data point, and the model's prediction-vs-target comparison can be turned into data points by a collector, but the prediction itself is not.
- Not a snapshot of LLM output. If a 0.3 process generates text, that text is not a data point. A 0.1 collector walking that text and computing structured measurements over it can produce data points; the prose itself cannot.

## Why this shape

Each field exists to close a specific class of hallucination:

- `id` + `witness` close *silent edit* — a hand-rewritten record fails witness recomputation.
- `kind` + per-kind schema close *type drift* — a collector cannot quietly start emitting differently-shaped values under the same name.
- `provenance.collector` as pointer (not prose) closes *orphaned claims* — every data point traces to a real, runnable program.
- `provenance.source_state` closes *unanchored measurement* — every value names what it measured.
- The no-LLM guarantee closes *circular grading* — the bedrock cannot be a model's output, because a model's output is what we are trying to fence.

Holding all of these at once is what makes the bottom of the ladder un-second-guessable. A higher rung that depends on a data point depends on something that can be re-derived from public source by anyone, with no model in the loop.
