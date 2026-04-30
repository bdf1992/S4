# Foundation 3 — Pointer shape

**Status:** hardcoded after Move 1 commit. Immutable for the rest of this experiment. Any change to this file is itself a 0.4 grading event and must be logged explicitly, not silently revised.

---

> **Un-grounding disclosure (Event 001 rejected, 2026-04-29).** This foundation is hardcoded from [CLAUDE.md](../CLAUDE.md) without external-standard citation. Event 001 documented the gap that the bedrock spec files were synthesized rather than anchored against published standards. Pointer-shape was not itemized in the Event 001 affected-foundations table (no equivalent published spec was identified for the cross-rung-pointer abstraction), but the broader un-grounding disclosure applies. The event was **rejected** per operator decision and the bedrock remains as authored. See [grading-events.md Event 001](grading-events.md) for the rejected proposal and re-trigger conditions.

---

## What a pointer is

A pointer is the only legitimate way for one rung to refer to another rung's artifacts. Whenever a 0.1 collector cites the source it walked, a 0.2 dataset row records its origin, a 0.3 plan step justifies a decision, or a 0.4 bundle reports its dependencies — the reference is a pointer, computed at use-time, not a sentence.

A pointer is not a citation. A citation is prose that names a target. A pointer is a structured record that *resolves* against current state and reports `live` or `dangling` deterministically. Citations rot silently; pointers fail loudly.

A pointer is the load-bearing primitive that makes the running-order rule from CLAUDE.md mean anything. Mutual support between rungs requires that each rung can ask "are the things I depend on still there?" and get a real answer. Pointers are how that question is asked.

## Shape

A pointer is a record with exactly these fields. A record missing any field, or carrying additional fields, is not a pointer.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `kind` | string | yes | What category of thing this points at. Each kind has exactly one resolver. Examples: `file_line` (a `path:line` location), `symbol` (a named code symbol), `data_point` (a Foundation-1 record by `id`), `collector` (a Foundation-2 program), `dataset_row`, `signal`. |
| `target` | typed-by-kind | yes | The identifier of the pointed-at thing. The format is fixed by `kind`; e.g. for `file_line`, a `{path, line}` pair. A target whose format does not match its kind is malformed. |
| `resolver` | string | yes | The `collector_id` (or equivalent declared name) of the 0.1 program that resolves pointers of this `kind`. Resolvers are themselves collection programs (Foundation 2) and are subject to the same audit. One kind → one resolver. |
| `bound_at.source_state` | string | yes | The source-state identifier under which the target was resolved live, if ever. May be `null` only on construction, before first resolution. After first live resolution, this field is set and never silently overwritten — a re-resolve at a new source state produces a *new* pointer record, not a mutation of an old one. |
| `bound_at.resolved_at` | ISO-8601 timestamp | yes | Wall-clock of the most recent successful resolution. Advisory only; freshness is judged by source_state, not by this. |
| `last_status` | enum: `live` \| `dangling` \| `unresolved` | yes | The result of the most recent resolution attempt. `unresolved` is the construction-time default, before any resolver call. |
| `last_payload` | typed-by-kind \| null | yes | On `live`: the payload the resolver returned (e.g. for `file_line`, the line's content; for `data_point`, the data-point record). On `dangling` or `unresolved`: `null`. |
| `last_reason` | string \| null | yes | On `dangling`: a structured reason code emitted by the resolver (e.g. `path_missing`, `line_out_of_range`, `symbol_renamed`, `source_state_unknown`, `schema_mismatch`). On `live` or `unresolved`: `null`. |

There is no free-text description, no human comment, no "intent" field. If a 0.3 process wants to record *why* it created the pointer, it does so in its own log, not inside the pointer.

## Guarantees a valid pointer provides

1. **Deterministic resolution.** The resolver is a Foundation-2 collector. Given the pointer and a source_state, the resolver returns the same `(status, payload, reason)` every time. No model in the loop.
2. **Binary status.** Resolution is `live` or `dangling`. There is no "probably live", no "stale but maybe still right", no confidence score. (Confidence is a 0.2 concern; resolution is 0.1.)
3. **Structural target.** `target` parses against its `kind`'s declared format. A reader can extract every component (path, line, symbol, id) without natural-language parsing.
4. **No silent freshness.** `last_status` is meaningful only at the recorded `bound_at.source_state`. A consumer treating it as live without checking the source_state is misusing the pointer; the pointer itself never claims more than it knows.
5. **Append-only history at use-time.** Resolving a pointer at a new source_state produces a new pointer record (or, equivalently, a new resolution event for the same logical target). The previous pointer's fields are not mutated. This makes pointer behavior over time itself an inspectable trace, not a mystery.

## Resolution protocol

A pointer is resolved by calling its declared resolver with `(target, source_state)`. The resolver returns one of:

- `("live", payload)` — the target was found at `source_state`, exactly as `target` describes it. `payload` is the resolver-typed payload (e.g. file line text, data-point record).
- `("dangling", reason)` — the target could not be found, or was found in a form that does not match `target`. `reason` is one of a fixed enum declared by the resolver (no free-text reasons).

A resolver MAY NOT return any other shape. It MAY NOT return "partial", "approximate", or "best-match" results. If it cannot give a binary live/dangling answer, it is not a resolver.

After resolution, the pointer's `last_status`, `last_payload`, `last_reason`, and `bound_at.{source_state, resolved_at}` fields are updated by writing a new pointer record (or a new resolution event for the same logical pointer); the prior record is preserved.

## Detectable violations

| Violation | How it is detected |
| --- | --- |
| Missing or extra top-level field | Schema validator rejects the record. |
| `target` does not match the format declared by `kind` | Per-kind target validator rejects the record. |
| `resolver` does not name a registered, valid collector for this `kind` | Resolver-registry check; reject. |
| Resolver violates Foundation 2 (e.g. imports an LLM SDK) | Fold into the collector-validity check; the pointer is unsafe and rejected. |
| Resolver returns a shape other than `("live", payload)` or `("dangling", reason)` | Runtime check on the resolver's output; reject the pointer's resolution and treat the resolver as broken. |
| Pointer is *authored as prose* — i.e. it appears as a sentence in a markdown file rather than as a structured record produced by a resolver call | Two-part check: (a) source files containing what looks like a pointer (e.g. matching the `path:line` regex) are scanned; (b) each candidate must have a corresponding pointer record produced by a resolver. Prose mentions without a resolver record are flagged as citations, not pointers. |
| `last_status` is `live` but a fresh resolution at the *current* source_state returns `dangling` | Freshness audit: re-resolve and compare. The pointer is reclassified; downstream consumers are notified. The original record is not mutated; a new resolution event is recorded. |
| Two pointers have the same logical identity but contradictory `last_status` at the same source_state | Cross-record consistency check; one of the resolutions is wrong and the resolver is the suspect. |
| Pointer resolution is influenced by anything other than `target` and `source_state` (e.g. environment variable, time, prior calls) | Determinism check: resolve in two clean environments at the same source_state; diff the results. Non-empty diff = violation. |

A pointer that fails any check is not used. Whatever depended on it is now unsupported and must be re-resolved (or invalidated) by a known-good resolver.

## Live vs dangling vs unresolved

- **live** — the most recent resolution at the recorded `bound_at.source_state` returned `("live", payload)`. The pointer is good *for that source_state*. Whether it remains good at a newer source_state is unknown until re-resolved.
- **dangling** — the most recent resolution returned `("dangling", reason)`. The pointer is broken at the recorded source_state. A higher rung that depended on this pointer must either accept the breakage and invalidate, or re-author the target and re-resolve.
- **unresolved** — the pointer record exists but has not yet been resolved. This is a transient state during construction; a pointer that stays `unresolved` is a bug in whatever built it.

Note the asymmetry: `live` is a claim about a *past* source_state; it does not claim freshness against the *current* source_state. Higher rungs that need current-source guarantees must re-resolve at use-time, not trust an older `live`. The default behavior of any 0.3 process that consumes a pointer is to re-resolve before relying on it; trusting a stale `live` is a higher-rung discipline failure, not a pointer-shape failure.

## What a pointer is not

- Not a citation. A markdown sentence like "see `foo.py:42` for the implementation" is a citation. It can become a pointer only by being produced as a structured record from a resolver call against current source.
- Not a hyperlink. A clickable link in a doc is a navigation aid. It has no resolver, no live/dangling status, no source_state binding. It can rot silently. Useful for humans, useless as bedrock.
- Not a foreign key. A foreign key in a database refers within a closed schema. A pointer refers across rungs and across source generations; its resolver, not a referential-integrity constraint, is what makes it work.
- Not free-form. There is no `notes`, no `description`, no `intent`. A pointer says exactly what it points at and what happened when it was resolved. If something else needs saying, a different record kind says it.

## Why this shape

Each constraint exists to close a specific failure mode:

- Computed-not-authored closes *citation rot*. A sentence in a markdown file claiming `foo.py:42` exists keeps claiming it after the file is deleted; a pointer that rots becomes `dangling` the next time it is resolved, and downstream consumers find out.
- Binary status closes *fuzzy referencing*. "Probably still there" is exactly the kind of claim that lets the bedrock erode. Either the resolver finds the target or it doesn't.
- Single-resolver-per-kind closes *resolver drift*. If two programs both claim to resolve `file_line` pointers, they will eventually disagree, and there will be no fact of the matter. One resolver per kind keeps resolution well-defined.
- Append-only resolution history closes *silent change*. A pointer that flips `live` → `dangling` over time leaves a trace; a reader can see when it happened and why.
- The mandatory `last_reason` enum closes *vague breakage*. A dangling pointer says exactly why it dangles, and the set of reasons is closed (declared by the resolver), so the next rung up can branch on the reason without parsing prose.

Holding all of these at once is what makes mutual pointing between rungs (the running-order rule from CLAUDE.md) actually work. Without these, "rung A points at rung B" is just a sentence; with these, it is a runnable fact.
