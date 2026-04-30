# Overnight session — 2026-04-30

## Iteration 1

**Goal:** Write the derived proposal contract that gates 0.3 → new 0.1 promotion.

**Result:** committed [foundations/proposal.md](../foundations/proposal.md) at `74d7131`.

**Why this first.** Every later iteration depends on the contract: gap-collectors emit data points that proposals point at; proposal manifests need a defined schema before any candidate can be drafted. With the contract on disk, iterations 2+ can proceed against a stable spec instead of re-litigating the shape.

**Shape choices worth flagging for operator review tomorrow:**
- `proposal_id` format is `prop:YYYY-MM-DD:slug` — slug is `[a-z0-9-]+`, no length cap declared. If you want a length cap, that's a one-line edit.
- `candidate/sample/` is required non-empty. A candidate with zero samples is rejected at draft-time, treating "no inputs that round-trip" as definitionally not yet a 0.1 fence (per zero-four.md §0.0→0.1).
- Promotion is mediated by a 0.1 promoter program *separate from* any 0.3 routine. The contract specifies "small, deterministic" but the promoter itself is not yet written. Iteration N will need to draft it (under proposals/, then promote itself by hand once — a fun bootstrap moment).
- The contract is marked DERIVED, not bedrock. It can be revised without a 0.4 grading event. This is intentional — the four bedrock foundations are immutable, but wiring on top of them is allowed to evolve as the experiment teaches us.

## Gaps measured

None this iteration — the gap-collector itself doesn't exist yet (iteration 2's work).

## Proposals drafted

None this iteration — preconditions (contract + at least one gap-collector + at least one gap data point) not all met.

## Blockers

None.

## Next iteration should pick up

**Step 2 from the loop spec:** write the first gap-collector at `skills/gap_audit/collectors/claim_without_probe.py`. Foundation-2 collector. Inputs: `skills/claim_audit/outputs/`, `skills/claim_audit/datasets/`. Walks claim_audit's most recent output, joins against whatever probe-registry exists (or notes its absence as a higher-order gap). Emits `kind=claim_without_probe` data points. Add `skills/gap_audit/collectors/sample/` with a runnable input.

**Pre-work:** the next iteration must read [skills/claim_audit/](../skills/claim_audit/) (SKILL.md, dataset shape, output shape) before writing collect(), so the gap-collector's inputs match the actual schema claim_audit produces — not a guessed schema.

## Operator decisions needed

None this iteration.

---

## Iteration 2

**Goal:** Write the first gap-collector at [skills/gap_audit/collectors/claim_without_probe.py](../skills/gap_audit/collectors/claim_without_probe.py).

**Result:** committed [skills/gap_audit/](../skills/gap_audit/) at `e16c97d`. 8 files, ~347 insertions. Layout mirrors the each-skill-has-its-own-lib convention (claim_audit, regime_audit). Collector is ~70 substantive lines, under the 80-line audit budget.

**Pre-work done:** read claim_audit's SKILL.md, dataset shape (`md_link` records), collector idiom (top-level constants + `compute_source_state()` + `collect()` + `verify()` + self-pointer helper), and lib structure. Vendored `lib/data_point.py` and `lib/pointer.py` from claim_audit verbatim — same files, copied per the existing convention rather than imported across skill boundaries.

**Sanity check against live data:**
```
COLLECTOR_ID: claim_without_probe
KIND: claim_without_probe
INPUTS: ['skills/claim_audit/datasets/markdown_claims.jsonl', 'skills/claim_audit/datasets/markdown_claims.source_state']
source_state: sha256:d9a8b56861b1673f...
emitted 0 claim_without_probe data points
determinism: witnesses match across re-runs ✓
```

The collector is structurally correct, deterministic, and runs cleanly. **It emits 0 records today** because the current live `markdown_claims.jsonl` has 252 `live` / 10 `external` / 5 `dangling_file` / **0 `anchor_unverified`** records. The collector reports honestly: there is no anchor-verification gap in the current dataset state.

This is informative, not a failure. Two readings worth your attention tomorrow:
- The dataset on disk may be stale — files added since the last claim_audit run (e.g. `foundations/proposal.md` written this iteration) aren't reflected. A fresh `claim_audit` orchestrate run would likely surface anchor_unverified records, since the new prose has section-anchored links. **The loop did NOT re-run claim_audit's orchestrator** — that's modifying an existing skill's persisted state, which the loop's hard constraints forbid. Refreshing the upstream dataset is your call.
- The 5 `dangling_file` records are claims-with-probes-that-say-broken — a different kind of actionable gap. They are not picked up by this gap-collector by design (the probe ran; the answer is just "no"). Whether to add a sibling gap-collector for "broken claims" is a scope question.

## Gaps measured

Zero gap data points emitted by the live claim_audit dataset state. The pipeline is wired; it just has no work to do until the upstream dataset has anchor_unverified records.

## Proposals drafted

None — no gap data points to anchor proposals against.

## Blockers

None hard. One soft tension flagged for review (below).

## Next iteration should pick up

**Step 3 from the loop spec:** persist gap-collector output. Even with zero records emitted, write `skills/gap_audit/datasets/2026-04-30/claim_without_probe.jsonl` (empty file or zero-length jsonl is honest). Then commit. This makes the collector's output a structured artifact the operator-review tomorrow can point at, rather than a one-shot Python invocation.

**If iteration 3 finds zero records again,** consider scoping out: emit a `bundle_health` style note in the session log that the gap pipeline has nothing to do *until* upstream conditions change, then either no-op subsequent iterations or attempt step 4 against a different gap source if one becomes obvious.

## Operator decisions needed

1. **Sample-mechanism design** *(soft tension; iteration 2 made an interim choice)*. The proposal contract requires `candidate/sample/` non-empty with "inputs `collect()` produces well-formed output for." The existing claim_audit / regime_audit skills do NOT carry their own sample/ — their convention is "the live dataset is the sample." I wrote a synthetic input + a markdown note describing the expected `collect()` behavior, but did NOT introduce a sample-runner harness (which would require the collector to accept input redirection, conflicting with Foundation 2's fixed-INPUTS rule). Three options for tomorrow:
   - (a) Refine the proposal contract: clarify that `sample/` is a *declarative* artifact (synthetic input + expected-shape note) rather than a runnable harness — matches what's there now.
   - (b) Introduce a sample-runner pattern: a small companion script per collector that monkeypatches REPO_ROOT for the duration of a sample run, kept under audit budget. Adds infrastructure but makes samples directly executable.
   - (c) Reinterpret `sample/` as a pointer to the live dataset directory: i.e., `candidate/sample/` is empty and `proposal.json` carries a `sample_pointer` field pointing at the candidate's first run output. Most consistent with existing convention but requires the candidate to have already run, which is iteration 3+ work.

2. **Gap-collector scope** *(decision punted to iteration 3 unless flipped)*. Should `claim_without_probe.py` also surface `dangling_file` records, or is that a different concept (broken-claim) that wants its own collector? Current collector deliberately covers only `anchor_unverified`. Splitting keeps each collector single-purpose; merging gives the operator one place to look.

3. **Upstream dataset refresh** *(loop respected the hard constraint, deferring to you)*. The live `markdown_claims.jsonl` predates this overnight session. A fresh claim_audit run would likely populate `anchor_unverified` records (the new prose under `foundations/proposal.md` has section-anchored links). Whether to refresh is an operator action; the loop won't touch existing skills' persisted state.
