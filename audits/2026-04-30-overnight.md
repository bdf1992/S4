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
