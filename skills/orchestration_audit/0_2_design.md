# 0.2 Design — Trace-Conformity Signal for orchestration_audit

**Status:** design committed before implementation. Earns its weight only after [collectors/orchestration_activations.py](collectors/orchestration_activations.py) (Prereq A) and [collectors/decision_point_honesty.py](collectors/decision_point_honesty.py) (Prereq B) — both in place as of commits `4d50512` and `a2ef5bd`.

## Why this signal exists

A 0.3 orchestration emits a run that is a sequence of (decision_id, fence_id, verdict, branch_taken) activations against 0.1 fences, ending in a `run_claim` (`candidate`, `healthy`, `aggregated`, `unleashed`, `rejected`, or eventually `0.4`). The 0.2 question this signal answers: **does this run's trajectory match the shape of past runs that emitted at the highest claim level its skill family has seen?**

This is the "0.4 needs a 0.2 signal to fire" rule from [foundations/zero-four.md:178](foundations/zero-four.md#L178), made operational. Today's `emission_readiness` signals satisfy the rule by threshold — this signal would satisfy it by **trace-conformity arbitrated by a gradient-fitted graph of state-based machines**, which is the strict mechanism criterion.

## Inputs

The signal consumes Foundation-1 data points of two kinds, both produced by collectors in this skill:

- `orchestration_activation` — one record per fence consultation in a run. Carries `decision_id`, `fence_id`, `branch_taken`, `verdict`, `confidence`, `sequence_index`, `run_claim`. (54 records across 24 runs at design time.)
- `decision_point_honesty` — one record per `(skill_id, decision_id, fence_id)` tuple. Carries source-presence locations and corpus-observed branch/verdict diversity. (12 records at design time.)

Activations are the trajectory; honesty measurements are the **edge-quality weights** — a transition through a tuple with `branch_diversity == 1` carries less arbitration signal than one through a tuple with `branch_diversity > 1`.

## Architecture

The signal is a **probabilistic finite-state machine (PFSM)** over the trace, with parameters fit by gradient on trace likelihood. State-based machines are the decision_ids; transitions are conditioned on `(fence_id, verdict, branch_taken)` triples; the run-end aggregator produces a softmax over `run_claim` classes.

```
   ┌─ decision node ──┐  e_ij = w(fence_id, verdict_i, branch_taken_j)
   │  decision_id_k   │  fitted by gradient against MLE of trace + label
   │  embedding(d)    │
   └────────┬─────────┘
            │  edges parameterized per (fence, verdict, branch)
            ▼
   ┌─ next decision ──┐
   │  decision_id_k+1 │
   └──────────────────┘
            │
            ▼
   [run-end aggregator]  →  softmax over {0.4, candidate, healthy,
                                          aggregated, unleashed, rejected}
                            verdict       = argmax
                            confidence    = max softmax probability
                            evidence_ptrs = top-k transitions by gradient magnitude
```

**Node count:** 8 decision_ids × small embedding (dim 4–8) + transition matrix shared across skills + per-skill head (4 skills × small linear) ≈ 50–100 parameters. Fittable on 24 runs with leave-one-run-out cross-validation.

**Why shared decision-id embeddings instead of per-(skill, decision) instances:** the corpus has only 1–2 runs per `(skill, decision)` tuple. Per-instance fits would memorize. Shared embeddings + per-skill heads share statistical strength while preserving skill-specific output mappings.

**Why edges parameterized per `(fence_id, verdict, branch_taken)`:** Prereq B's `branches_per_verdict` measurement tells us which transitions are observed-distinct vs observed-monotone. Transitions through monotone tuples get near-zero gradient signal automatically; transitions through diverse tuples get real fitting pressure. The honesty measurements are not a hard filter — they are an inductive bias.

## Training protocol

1. Load both datasets at a pinned `source_state`.
2. Build the trace per run: order by `sequence_index`, attach `run_claim` as label.
3. Construct PFSM with shared decision-id embeddings + (fence, verdict, branch) edge weights + per-skill linear head.
4. Loss: cross-entropy of softmax(head(aggregator(trace))) against `run_claim`, summed over runs.
5. Optimizer: gradient descent (Adam or SGD with momentum). Fixed seed for reproducibility.
6. Cross-validation: leave-one-run-out (24 folds). Report mean per-fold accuracy + macro-F1.
7. Persist fitted parameters as a Foundation-1 data point of kind `pfsm_parameters` (collector-emitted; the parameters are *measurements* of the optimization run at this corpus state, identified by source_state).

A fold-level fit producing a near-uniform softmax for some run is a signal — not a failure — that that run's trajectory is novel relative to the rest of the corpus. The model's *uncertainty* on a run is itself information the run-emitter wants.

## Typed query interface

```
signal.evaluate(trace) -> (verdict, confidence, evidence_pointers)
```

- `verdict` ∈ {`ready`, `not_ready`, `inconclusive`}.
  - `ready`: top-class softmax mass exceeds threshold AND top class is `0.4`.
  - `not_ready`: top class is one of {`candidate`, `rejected`} OR softmax is uniform within tolerance.
  - `inconclusive`: top class is a non-0.4 success class (`healthy`, `aggregated`, `unleashed`) — the trace looks well-formed for its skill family but the corpus has not yet tied that family to 0.4 emission.
- `confidence` ∈ [0, 1] = max softmax probability.
- `evidence_pointers`: list of (decision_id, fence_id, branch_taken) triples with the highest gradient contribution to the verdict, each pointing to its source-line locations from Prereq B's `decision_id_locations` / `fence_id_locations`.

When `verdict = not_ready`, the signal also returns a `gap_record`: structured naming of which corpus dimension is too thin (e.g., `{"missing_class": "0.4", "skills_with_class": []}`).

## Probe set

A fixed set of synthetic traces with recorded expected outputs, walked by `verify()` on every load:

1. **Empty trace.** Expected: `verdict=not_ready, gap_record={empty_trace: true}`.
2. **All-monotone trace** (every activation drawn from `branch_diversity == 1` tuples). Expected: `verdict=not_ready` or `inconclusive`; `evidence_pointers` should be sparse (low gradient weight on monotone edges).
3. **Trace with structural violation injected** (a `decision_id` not in any source). Expected: rejected upstream by Prereq B's structural check, never reaches the signal.
4. **Trace replayed from a known corpus run** (e.g., run-1fd685ad95366872). Expected: signal recovers the actual `run_claim` of that run with high confidence (training-set sanity check).

Probe inputs and expected outputs are recorded as data points; probe re-run is part of `verify.py` for the bundle.

## Known gaps at design time

| Gap | Evidence | Impact |
|---|---|---|
| 0 of 54 runs ended at `claim:0.4` | [datasets/orchestration_activations.jsonl](datasets/orchestration_activations.jsonl) profile | Model has no positive examples of its target class. First-run verdict will always be `not_ready` or `inconclusive`. |
| 9 of 12 tuples are monotone | [datasets/decision_point_honesty.jsonl](datasets/decision_point_honesty.jsonl) | Most edges have no fitting pressure. Model is structurally fittable but most of its parameters will sit near initialization. |
| Single corpus across 4 different skill families | activations corpus | Cross-skill transfer assumed; not verified. The per-skill head mitigates but does not eliminate. |
| 24 runs is small for any gradient fit | activations corpus | Cross-validation is mandatory; held-out accuracy reporting is mandatory; no claim of generalization without it. |

## Promotion criteria — what would have to grow before this signal can fire `ready`

1. **At least one run with `claim:0.4`** in the corpus, in any skill family. Without it, `verdict=ready` is unreachable by definition. Most direct path: promote one of the verifier proposals in [proposals/](../../proposals/), let the resulting bundle's verify.py run, and accept its emission if it passes.
2. **At least 3 runs per `(skill_family, run_claim)` cell** so cross-validation has a chance of meaningful fold structure. Today: leash_for_hooks has 5 runs all at `candidate`; leash_for_slash_commands has 4 runs (3 candidate, 1 rejected); claim_audit has 5 runs (split across healthy/rejected); regime_audit has 8 runs all at `aggregated`. Need diversity within skill family.
3. **At least one tuple per skill with `branch_diversity > 1`.** Today: 2 of 4 skills (both leashes) have at least one diverse tuple via `toggle_check`; claim_audit and regime_audit have zero. Without diversity, those skills' trajectories cannot exercise the model's transition weights at all.

Each of these is measurable. The signal's `gap_record` should report them in structured form on every `not_ready` run, so corpus growth across iterations is observable as a shrinking gap.

## What this design does NOT yet specify

- **The implementation library.** PFSM with gradient fit is doable in numpy alone (no autograd needed for this size); also doable in PyTorch/JAX for cleaner backprop. Choice deferred to implementation.
- **The persistence format for fitted parameters.** Will be a JSON record matching a `pfsm_parameters` value_schema — defined when the parameter-emitting collector is built.
- **The `0.4` threshold for `verdict=ready`.** Without any 0.4 traces in the corpus, the threshold cannot be calibrated. Will be set when the first 0.4 trace exists, by held-out probability of the held-out 0.4 trace under the trained model.
- **Whether to share transition weights across skills or not.** Initial implementation shares; if cross-skill transfer hurts more than it helps (measurable as worse leave-one-run-out accuracy with sharing on vs off), revisit.

These deferred items are noted explicitly so the implementation step has a clean punch list of what is committed and what is open.
