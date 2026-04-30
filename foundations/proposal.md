# Proposal contract — derived

**Status:** DERIVED. This contract is built on top of the four bedrock foundations ([data-point.md](data-point.md), [collection-program.md](collection-program.md), [pointer.md](pointer.md), [zero-four.md](zero-four.md)) and is revisable without a 0.4 grading event. It is NOT bedrock. The four foundations remain immutable; this file is the wiring under them for one specific 0.3 capability — drafting candidate 0.1 assets without admitting them to the live floor.

---

## What a proposal is

A **proposal** is a candidate 0.1 asset (a collection program per [collection-program.md](collection-program.md)) that a 0.3 routine has drafted in response to a *measured gap*, awaiting operator promotion before it joins the live floor.

A proposal is **not** itself a data point — it is authored by 0.3 — but every claim about it resolves to a data point. The proposal is wrapped in receipts so the operator's promotion decision rests on structure, not on prose.

A proposal lives under `proposals/{proposal_id}/` and is excluded from the live-floor pointer-resolver registry. Until promoted, no 0.4 bundle, no live collector, and no signal can depend on it. A 0.3 process may inspect proposals (e.g. to draft a successor), but may not consume their outputs as if they were live measurements.

The proposal mechanism exists to keep `0.3 → new 0.1` honest. Without it, a 0.3 routine that emits new collectors directly into the live floor is free-writing the bedrock — which is the anti-pattern [CLAUDE.md](../CLAUDE.md) names as "0.3 free-writing outside its declared 0.1+0.2 fences." With it, 0.3 *drafts*, 0.2 *gates* (via the operator-approval signal), and the operator *signs*. The leash stays on at the boundary that matters most.

## Shape

A proposal is a directory containing exactly the items in this table. A directory missing any item, or carrying additional items not declared here, is not a proposal.

| Item | Meaning |
| --- | --- |
| `proposal.json` | The manifest record. Fields are listed below. |
| `candidate/{name}.py` | The drafted 0.1 source. Must already pass [collection-program.md](collection-program.md)'s structural validators at draft-time (audit budget, no LLM SDK imports, no nondeterminism, declared `collector_id` / `kind` / `value_schema` / `inputs` / `collect()` / `verify()`). |
| `candidate/value_schema.json` | The declared schema for the proposed `kind`. Importable by the candidate. |
| `candidate/sample/` | Non-empty sample demonstrating the candidate's input → output relationship. The schema-validator-sample triplet from [zero-four.md](zero-four.md) §0.0→0.1 — without this, the candidate is a 0.0 free-write of a collector. **Two forms are accepted:** (a) *declarative* — a synthetic input file plus a markdown note describing the expected `collect()` output for that input (matches what existing skills like `claim_audit` carry as their effective sample, and what `gap_audit/collectors/sample/` carries today); (b) *runnable* — a small companion script under `sample/` that exercises `collect()` against the synthetic input and exits 0 iff the output count and shape are as expected. The runnable form requires a parameterized-INPUTS escape hatch in the candidate, which is not yet a Foundation-2 idiom; until that idiom is established, the declarative form is the default and is fully sufficient for the contract. |
| `gap.json` | List of pointers ([pointer.md](pointer.md)) to the data points that establish the gap this proposal claims to fill. The pointers' `kind` is `data_point`; the data points they resolve to are produced by gap-collectors in the live floor. |
| `pre_verification.json` | Structured output of running [collection-program.md](collection-program.md)'s validators against `candidate/` at draft-time. Produced by the 0.3 routine before the operator sees the proposal, so the operator never reviews a candidate that already structurally failed. |

## `proposal.json` fields

A record missing any field, or carrying additional fields, is not a valid proposal manifest.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `proposal_id` | string | yes | Stable handle. Format: `prop:{YYYY-MM-DD}:{slug}`. The date component is the source-state date when the gap was measured; the slug is short, `[a-z0-9-]+`. |
| `gap_pointers` | list[pointer] | yes | Pointers (`kind=data_point`) to the gap data points motivating this proposal. **Empty list is invalid.** A proposal with no measured gap is request-driven, not signal-driven, and is rejected at draft-time. |
| `candidate_pointer` | pointer | yes | `kind=collector`. Resolves to the candidate source under `candidate/`. |
| `claimed_kind` | string | yes | The data-point `kind` the candidate would emit if promoted. Must not collide with any live collector's declared kind (one-collector-per-kind, per [collection-program.md](collection-program.md)). |
| `pre_verification_pointer` | pointer | yes | `kind=data_point`. Resolves to a structured record showing every Foundation-2 validator passed at draft-time. |
| `proposed_at.source_state` | string | yes | The source state (git SHA or working-tree hash) at which the gap was measured and the candidate drafted. |
| `proposed_by` | pointer | yes | `kind=collector` or `kind=orchestration`. The 0.3 routine (or the orchestration step) that produced this proposal. |
| `status` | enum | yes | One of `proposed` \| `promoted` \| `rejected` \| `superseded`. Default on creation: `proposed`. State changes are append-only — a new manifest record, not a mutation of an old one. |
| `decision_record_pointer` | pointer \| null | yes | On `promoted` / `rejected` / `superseded`: pointer (`kind=data_point`) to the operator's approval-signal evaluation record. On `proposed`: `null`. |

There is no free-text `notes`, `reason`, or `description` field. If a 0.3 routine wants to record motivation, it does so in its own log; the proposal manifest stays structural.

## Promotion

Promotion is a 0.2 signal consultation, per [zero-four.md](zero-four.md) §0.2→0.3.

The signal is the **operator-approval signal**:

```
approval_signal.evaluate(proposal) -> (verdict, confidence, evidence_pointers)
where verdict ∈ {promote, reject, defer}
```

**First-run signal shape.** The signal's "training data" is `approvals/decisions.jsonl`, one decision record per line, written by the operator. The signal's evaluation is a deterministic lookup: if the operator has written a decision record for this `proposal_id`, return that record's verdict; otherwise return `defer`. This is honest about being a thin signal. Later iterations may fit a frequency table over decisions and start auto-`reject`ing obvious non-starters before the operator sees them — but the contract here is the typed query interface, not the family of signal underneath it.

**The leash stays on.** The signal cannot return `promote` without a corresponding operator decision record on disk. The 0.3 routine never auto-promotes; it never writes to `approvals/decisions.jsonl`; it never moves files out of `proposals/`. Promotion is the operator's signature, registered through the signal.

**On `promote`:** a small, deterministic 0.1 promoter program (separate from any 0.3 routine) moves `candidate/{name}.py` into the appropriate live collector directory, registers the kind in the live registry, re-resolves any pointers that targeted the proposal, and writes the new `decision_record_pointer` into a new `proposal.json` record with `status=promoted`.

**On `reject`:** `status` flips to `rejected`, `decision_record_pointer` is set, and the directory stays on disk for trace. A rejected proposal is not deleted; rejection is information that the next round of drafting consults.

**On `defer`:** no state change; the proposal remains `proposed`. The 0.3 routine sees `defer` and moves on.

## Guarantees a valid proposal provides

1. **Structurally pre-checked.** The candidate already passes [collection-program.md](collection-program.md)'s validators at draft-time. The operator never reviews a candidate that fails structurally; structural failures are caught and logged before the proposal is committed.
2. **Gap-anchored.** Every proposal cites at least one live gap data point. The gap is computed by a live gap-collector, not asserted by the 0.3 routine. A request-driven proposal cannot exist; the `gap_pointers` field rejects it.
3. **Promotion-gated.** No proposal becomes a live collector without an operator decision record routed through the operator-approval signal. The 0.3 routine has no path to the live floor that bypasses the signal.
4. **Append-only history.** Status changes produce new records, not mutations. The trace from `proposed` → `promoted` (or `rejected`, or `superseded`) is inspectable on disk.
5. **Bedrock-conforming candidate.** If promoted, the candidate enters the live floor having passed the same Foundation-2 validators a hand-written collector would. Promotion does not relax the bedrock; it only crosses the boundary.

## Detectable violations

Each violation MUST be detectable by a 0.1 program. A violation that requires human judgement, or a model's read, indicates a hole in this contract.

| Violation | How it is detected |
| --- | --- |
| Required field missing or extra field present in `proposal.json` | Schema validator on the manifest. |
| `gap_pointers` is empty | Schema validator: list length ≥ 1. |
| Any pointer in `gap_pointers` dangles at promotion-time | Pointer re-resolution against the current source_state. A dangling gap pointer means the gap is no longer measured live; the proposal is rejected. |
| `candidate/` fails any Foundation-2 validator at promotion-time | Re-run the full Foundation-2 validator suite at promotion. Do not trust draft-time `pre_verification.json` alone — the candidate may have been edited or the bedrock may have tightened. |
| `claimed_kind` collides with a live collector's kind | Live-registry check at promotion. |
| `status = promoted` but `decision_record_pointer` is null | Schema check on the promoted manifest. |
| `decision_record_pointer` resolves to a record whose `verdict` is not `promote` | Cross-record consistency check: a `promoted` proposal must point at a `promote` decision. |
| Proposal is prose-only (e.g. `candidate/` contains a markdown file describing the collector but no runnable Python) | Foundation-2 validator runs against `candidate/{name}.py`; absence of a runnable collector source fails at draft-time. |
| `proposed_by` is null or names a non-existent program | Pointer resolution. |
| `proposal_id` does not match the `prop:YYYY-MM-DD:slug` format | Format validator on the field. |
| Two proposal manifests share the same `proposal_id` but disagree on `gap_pointers` or `candidate_pointer` | ID-uniqueness check across the proposal store. (Status changes via append-only history are allowed; substantive disagreement on the underlying claim is not.) |
| Files appear under the live collector directory whose origin trace does not include a `promoted` proposal manifest | Live-floor audit: every live collector either pre-dates this contract or has a trace back to a `promoted` proposal. New live collectors without a trace are flagged. |

A proposal failing any check is not promoted. Whatever depended on it (typically: nothing, until promotion) is unaffected.

## What a proposal is not

- **Not a data point.** A proposal is authored by 0.3. Data points are computed by 0.1. The two do not become each other.
- **Not a live collector.** Until promoted, the candidate is on disk under `proposals/` but is invisible to the live registry, the live pointer resolvers, and any 0.4 verify.py. A 0.3 routine that imports from `proposals/` is consuming pre-bedrock material and is operating outside its fence.
- **Not a request.** The 0.3 routine cannot draft a proposal because the operator asked for one. It drafts a proposal because a gap-collector emitted a gap data point. Without a live gap data point, there is nothing for `gap_pointers` to point at, and the manifest fails the schema check.
- **Not bedrock.** This contract is derived. It can be revised when experience shows it should be. The four foundations remain the immovable layer; this file is wiring under them.
- **Not a TODO list.** A proposal is not a description of work the operator should do. It is a runnable candidate plus measured evidence that the candidate fills a real gap. If you cannot run the candidate, it is not a proposal.

## Why this shape

Each constraint exists to close a specific failure mode at the proposal-mechanism level (the foundations close failure modes at the primitive level):

- **Structural pre-check** closes *operator-as-validator-for-typos*. The operator's attention is finite; spending it on candidates that already failed Foundation-2 wastes it. The 0.3 routine's job is to filter to candidates worth the operator's read.
- **Mandatory gap pointers** close *request-driven 0.1*. A proposal with no measured gap is a 0.3 free-write claiming to be a 0.1 draft. The schema rejects it.
- **One-kind-per-collector at promotion** closes *kind drift*. If two proposals both claim the same kind, the second one's promotion is forced to either fail or supersede the first explicitly — never silently overlap.
- **Append-only status history** closes *promoted-then-changed*. A promoted proposal cannot be edited in place; supersession is a new record. The trace is inspectable.
- **Operator-approval as a 0.2 signal** closes *informal promotion*. Without a typed signal, "the operator approved" becomes a vibe; with one, it is a structured record at a known location, consultable by `verify.py` and by future 0.2 signals.
- **Promoter as separate 0.1 program** closes *write-during-decide*. The signal returns a verdict; a different program acts on it. Decision and effect are two events, not one.

Holding all of these at once is what lets the floor grow under discipline. A 0.3 routine can draft a hundred proposals overnight; the floor only grows by what the operator signs and what passes the bedrock checks. Generation is plentiful; promotion is scarce. That asymmetry is the point.
