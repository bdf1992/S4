# Foundation 4 — What makes a program 0.4

**Status:** hardcoded after Move 2 commit. Like the other three foundations, immutable for the rest of this experiment. Any change is itself a 0.4 grading event and must be logged explicitly.

This file uses only the vocabulary established in [data-point.md](data-point.md), [collection-program.md](collection-program.md), and [pointer.md](pointer.md). No new bedrock concepts are introduced; this file is the *composition rule* over the three foundations.

## What 0.4 is (positive definition)

A **0.4 bundle** is a directory containing:

1. **0.1 layer.** One or more collection programs (Foundation 2), each with its declared `collector_id`, `kind`, `value_schema`, `inputs`. The data points (Foundation 1) those collectors have produced, persisted in a data-point store under their `id`s. A pointer-resolver collector for every pointer kind referenced by anything in the bundle.

2. **0.2 layer.** One or more *signals*. A signal is a deterministic function whose input is a fixed shape (typically a candidate the orchestration is considering) and whose output is `(verdict, confidence, evidence_pointers)`. A signal's parameters — thresholds, frequency tables, learned weights, decision rules — are *fitted* to a dataset. The dataset is a set of data points produced by 0.1 collectors. Each signal carries a manifest entry naming its training-dataset pointers.

3. **0.3 layer.** Orchestration source. A program (or set of programs) that, when invoked, walks declared 0.1 inputs, queries declared 0.2 signals at declared decision points, and emits a *candidate artifact*. Every consultation is logged with the consulted fence and its result.

4. **Manifest.** A `manifest.json` listing every component in the bundle as a record carrying:
   - the component's role (`collector` | `signal` | `orchestration` | `dataset` | `denylist` | `output`),
   - a pointer (Foundation 3) to its source,
   - for collectors and signals, pointers to every dependency they declared,
   - for the bundle's emitted artifact, pointers to every fence the orchestration consulted while producing it.

5. **`verify.py`.** A self-contained 0.1 collector (subject to Foundation 2) that walks the manifest, runs the grading procedure below, and exits 0 iff the bundle conforms to this file. `verify.py` does not call a language model; it does not author judgement; it walks structure and reports.

6. **Emission gate.** A declared *emission-readiness signal* (a 0.2 signal) whose verdict gates whether the bundle is permitted to claim 0.4 status or only sub-0.4-candidate status. The gate's verdict is itself recorded in the manifest as a structured record (verdict + confidence + evidence_pointers).

A bundle that satisfies all six and whose `verify.py` exits 0 is a **0.4 bundle**. Anything else is, at best, a 0.4 candidate.

## The grading procedure

`verify.py` runs the following algorithm. Every step is deterministic; there is no model in the loop. Failure of any step results in non-zero exit and a structured failure record naming the failing component and the violation class.

```
1. Load manifest.json. Validate schema. Reject if malformed.

2. For each entry of role "collector":
   2a. Resolve its source pointer. Reject if dangling.
   2b. Run the Foundation-2 validator on the resolved source:
       - declared collector_id, kind, value_schema, inputs, collect, verify
       - audit budget
       - LLM-SDK denylist (consulting data points, not prose)
       - nondeterminism scan
   2c. Run the collector twice in clean environments at the same source_state.
       Diff outputs. Reject on non-empty diff.
   2d. Emit one self-check data point per collector: pass/fail.

3. For each entry of role "dataset":
   3a. Resolve every pointer in the dataset. Reject if any dangle.
   3b. For each data point referenced:
       - Validate Foundation-1 schema conformance.
       - Re-derive against its provenance.source_state via its collector's
         collect(). Reject on value/witness mismatch.
   3c. Emit one self-check data point per dataset: pass/fail.

4. For each entry of role "signal":
   4a. Resolve its source pointer. Reject if dangling.
   4b. Resolve every training-dataset pointer. Reject if any dataset's
       step-3 self-check failed.
   4c. Run the signal on a declared probe set (small fixed inputs whose
       expected outputs are themselves data points). Reject on mismatch.
   4d. Emit one self-check data point per signal: pass/fail.

5. For each entry of role "orchestration":
   5a. Resolve its source pointer. Reject if dangling.
   5b. Inspect the orchestration's declared decision points. For each
       decision point, verify that the source consults a declared 0.1
       collector or 0.2 signal at that point (structural check on the
       source — it is short enough to make this check tractable; if not,
       it violates the orchestration audit budget below).
   5c. For the bundle's emitted artifact, walk the orchestration log.
       Verify every claim in the artifact carries a pointer back to the
       fence consultation that produced it.
   5d. Emit one self-check data point per orchestration: pass/fail.

6. Run the emission-readiness signal on the bundle. Record its verdict +
   confidence + evidence_pointers. If verdict != "ready", verify.py
   still exits 0 *as a sub-0.4 candidate verification* — but the bundle
   is barred from claiming 0.4 status. The manifest's claim flag is set
   to "candidate", not "0.4".

7. For every pointer anywhere in the bundle, re-resolve at the current
   source_state. Record live/dangling. If any pointer the manifest
   marked "load-bearing" is dangling, reject.

8. Aggregate. If steps 2-5 and 7 all passed:
   - And step 6's verdict was "ready": exit 0, emit manifest claim "0.4".
   - And step 6's verdict was not "ready": exit 0, emit manifest claim
     "candidate", with the specific gap recorded.
   Otherwise: exit non-zero, emit a structured failure record.
```

The grading procedure is the algorithm. `verify.py`'s job is to execute it; everything else in the bundle is in service of giving `verify.py` something tractable to walk.

## Negative definition (what disqualifies a candidate)

A bundle is **not** 0.4 if any of the following hold. Each is a single, mechanically-detectable predicate on the bundle.

| Disqualifier | Detection |
| --- | --- |
| Any collector fails the Foundation-2 validator | Step 2b above. |
| Any data point fails re-derivation against its recorded source_state | Step 3b above. |
| Any signal's parameters were *authored* (not fitted to a dataset of data points produced by 0.1 collectors) | Step 4b above (no training-dataset pointer that resolves to a 0.1-collected dataset = author-fit signal = reject). |
| Any 0.3 decision point free-writes outside its declared fences | Step 5b above (structural inspection of orchestration source). |
| Any claim in the emitted artifact lacks a pointer back to the fence that produced it | Step 5c above. |
| Any load-bearing pointer dangles | Step 7 above. |
| `verify.py` itself violates Foundation 2 (imports an LLM SDK, exceeds audit budget, etc.) | `verify.py` is itself a collector and is run through the same validator at bundle-level boot. A self-grading walker that lies is a dead bedrock. |
| The bundle's manifest describes components that do not exist on disk | Pointer-resolution fails on load. |
| The bundle declares a "0.4" claim while the emission-readiness signal returned not-ready | Step 6 above; manifest claim is forcibly downgraded to "candidate". |
| The bundle has no emission-readiness signal at all | Step 6 cannot run; reject as missing required structure. |

The asymmetry to notice: failing the emission-readiness signal does *not* invalidate the bundle as engineering — it just downgrades the claim. A sub-0.4 candidate with all 0.1/0.2/0.3 components verified and a clean walker is still a real artifact; it simply cannot stamp itself "0.4" until the signal says the conditions are met. This is what makes "0.4 is driven by 0.2, not by request" operational: the request can produce a candidate, but only the signal can promote it.

## Chosen inter-layer constraint patterns

Per CLAUDE.md, the constraint patterns between adjacent rungs are *relatively-defined* — not a uniform prescription. Here is the wiring chosen for the leashes built under this experiment. These patterns are the wiring, not the bedrock; a future leash for a domain that genuinely demands a different pattern can choose a different one and explicitly log the choice.

### 0.0 → 0.1: schema-validator-sample triplet

A 0.0 free-write becomes 0.1 when fenced by:
- a declared **schema** (the shape of valid output),
- a deterministic **validator** that runs against the schema and rejects malformed inputs,
- a non-empty **sample** of inputs the validator passes on (the sample itself is a data point produced by a sample-collector).

Generation under this fence: a 0.3 process may produce candidate output, but it is rejected unless the validator passes. A schema with no validator, or a validator with no sample, or a sample with no source — none of those is a fence. All three together are.

### 0.1 → 0.2: dataset-pointer required at fit-time

A 0.2 signal's parameters are fitted to a *dataset*: a collection of same-kind data points conforming to a single value_schema, all produced by 0.1 collectors. The signal's manifest entry MUST declare:
- a pointer to the training-dataset (resolves to a 0.1-collected dataset),
- the fitting procedure as a deterministic 0.1 program (so refitting is reproducible),
- a *probe set*: a small fixed set of inputs whose expected outputs are recorded as data points, so `verify.py` can check the signal still does what it did at fit-time.

A signal whose training-dataset pointer dangles, or whose probe set fails on re-run, is not a valid signal.

### 0.2 → 0.3: typed query interface, mandatory consultation, logged result

A 0.2 signal exposes a single typed entry point: `signal.evaluate(input) -> (verdict, confidence, evidence_pointers)`.

- `verdict` is drawn from a closed enum the signal declares.
- `confidence` is a value in [0, 1] (or another bounded scale the signal declares).
- `evidence_pointers` is a list of pointers (Foundation 3) to data points whose presence in the training dataset most strongly influenced this verdict.

0.3 orchestration is required to:
- Declare its decision points up front (where in its own source it will consult signals).
- Call exactly the declared signals at exactly the declared decision points (structural check).
- Include the full `(verdict, confidence, evidence_pointers)` of each consultation in the emitted artifact's log.
- Branch on the verdict via a closed match — no fall-through, no silent ignore.

A 0.3 program that consults a signal but ignores its verdict is operating outside its fence; that is a violation, not a judgement call.

### 0.3 → 0.4: manifest + emission-readiness gate

A 0.3 emission becomes a 0.4 bundle only when:
- The orchestration's emission step writes a `manifest.json` enumerating every component depended on (collectors, datasets, signals, orchestration source itself, the emitted artifact).
- The emission-readiness signal is consulted as the final fence and its verdict + confidence + evidence_pointers are recorded.
- `verify.py` exits 0 with the "0.4" claim flag set.

If the emission-readiness signal returned not-ready, the bundle is emitted as a candidate, the manifest's claim flag is "candidate", and the gap is recorded. The candidate is a legitimate output of the 0.3 layer — just not a 0.4 output.

## The orchestration audit budget

For step 5b's structural check on orchestration to be tractable, 0.3 orchestration source files are subject to an audit budget similar to (but looser than) Foundation 2's collector budget:

- A single orchestration entry point: at most one screenful of substantive code (target ≤ 150 lines excluding imports, schema, and tests).
- Decision points declared as a top-level constant (a list of `(decision_id, fence_id)` pairs) so the structural check is a one-pass scan.
- No dynamic dispatch over fences (no "look up the signal by name from a string at runtime" without that name appearing in the declared decision-points list).

Helpers are allowed but must themselves be small enough to inspect. An orchestration entry point that grows past the budget is split into two declared-and-pointed leashes, not refactored into a black box.

## The 0.2-drives-0.4 rule, made operational

CLAUDE.md says: "A 0.4 emission requires a 0.2 signal to fire. You do not produce 0.4 because someone asked for it."

This is realized by the **emission-readiness signal**: a 0.2 signal each leash is required to declare. Its job is to look at the dataset coverage, the strength of the signals consulted during this run, and the candidate the orchestration is about to emit, and return:

- `("ready", confidence, evidence_pointers)` when the signal's training data covers the situation densely enough and the bundle's checks all came back strong, OR
- `("not_ready", confidence, evidence_pointers, gap_record)` when coverage is thin, signals were borderline, or some declared check returned weak — `gap_record` names what specifically is missing.

A first-run leash, by construction, has a thin training dataset and weak signals. The honest verdict is `not_ready`, the bundle is a candidate, and `gap_record` says exactly what would have to grow for the next run to be ready. This is how floor-growth becomes measurable: the gap_record from run N is the input to what the 0.1 layer must collect more of before run N+1 can claim 0.4.

## Sub-0.4 candidate is a real output

A bundle whose `verify.py` exits 0 with claim "candidate" is *not* a failure. It is a legitimate output of the 0.3 layer that has done all the engineering 0.4 requires *except* that the dataset is too thin for the emission-readiness signal to fire. Every collector ran, every data point re-derived, every pointer resolved live, every signal's probe set passed, every orchestration decision was logged with its consulted fence. The bundle is engineered; it just isn't yet 0.4.

This distinction matters because:
- It prevents the "fail to emit anything" trap. A leash on its first run still produces a candidate, and the candidate is the input the 0.1 layer needs to grow against.
- It prevents the "emit a fake 0.4" trap. A candidate is honest about what it isn't.
- It makes floor-growth visible round-over-round. Run 1 candidate → run 2 candidate or 0.4 → if 0.4, the floor grew enough to flip the gate; if still candidate, the gap_record names what's still missing.

## What this file does NOT specify (intentional, deferred)

- **Per-domain `kind` taxonomies.** Each leash declares its own kinds (e.g. `hook_config`, `slash_command_decl`, `claude_md_section`). This file says nothing about what kinds exist; it only requires that each is fixed once.
- **Persistence format for the data-point store.** JSON, sqlite, jsonl — the choice is per-leash. Foundation 1's shape is the constraint, not the storage.
- **Specific signal families.** The first leash uses small statistical signals (frequency tables, threshold rules) because the data is thin and the dimensionality is low. Future leashes may use richer 0.2 families if their dataset and dimensionality justify it. The constraint is the typed query interface, not the model class.
- **The form of the emitted artifact.** A leash for hooks emits a settings.json fragment. A leash for slash commands emits a SKILL.md. A leash for CLAUDE.md emits an overlay. The artifact shape is per-domain; the manifest + verify.py contract is universal.

## Why this composition rule

Each piece exists to close a specific failure mode at the *bundle* level (the foundations close failure modes at the *primitive* level):

- The manifest closes *implicit dependency*. A bundle that doesn't enumerate what it depends on is a bundle whose dependencies cannot be re-resolved later.
- `verify.py` as a collector closes *self-grading without a fence*. The walker is held to the same standard as the things it walks.
- The emission-readiness gate closes *vibes-driven 0.4*. A request-driven emission is a 0.0 free-write dressed up; a signal-driven emission is one where the bedrock decided.
- The candidate-vs-0.4 distinction closes the *all-or-nothing trap*. First-run leashes can emit something legitimate while the floor grows toward what 0.4 actually requires.
- The chosen inter-layer patterns close *unconstrained generation*. 0.3 has fences at every adjacent rung; the fences are typed, runnable, and inspectable.

Holding all of these at once is what lets a 0.4 bundle be walked by 0.3 and verified — which is what CLAUDE.md says is the litmus: "If 0.3 cannot walk it, it is not 0.4."
