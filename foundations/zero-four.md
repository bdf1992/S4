# Foundation 4 — What makes a bundle 4.0, and what 0.4 produces

**Status:** hardcoded after Move 2 commit. Like the other three foundations, immutable for the rest of this experiment. Any change is itself a 4.0 grading event and must be logged explicitly.

---

> **Un-grounding disclosure (Event 001 rejected, 2026-04-29).** This foundation is hardcoded from [CLAUDE.md](../CLAUDE.md) without external-standard citation. Event 001 documented the gap (in particular the orchestration "audit budget ≤ 150 LOC" rule was authored, not anchored against McCabe cyclomatic complexity or Pylint/Ruff defaults) and was **rejected** per operator decision: the 4–6h migration would have frozen in-flight sibling-leash work without a corresponding 2.0 signal that the grounding is needed yet. The bedrock remains as authored. See [grading-events.md Event 001](grading-events.md) for the rejected proposal and re-trigger conditions.

> **Vocabulary-lift disclosure (Event 002 in progress, 2026-05-01).** This file was lifted from the pre-2026-05-01 single-axis "ladder of regimes" framing to the two-axis programs-vs-protocols framing established in CLAUDE.md (programs are X.0 — 1.0 handwritten, 2.0 learned, 3.0 prompted, 4.0 coupled; protocols are 0.X — 0.1, 0.2, 0.3, 0.4; 0.0 is the candidate state). **The shape, guarantees, validations, and grading procedure are unchanged.** Only the language is updated. See [grading-events.md Event 002](grading-events.md) for the lift event log.

> **Independent-validation disclosure (Event 003 in progress, 2026-05-02).** This file now separates production from final claim validation. Lower-layer 0.1 and 0.2 validators remain required, but once their validator/receipt files exist they are independent proof surfaces the 0.4 walker can point at; they are not synchronous blockers for unrelated work. The blocking checks are the produced 0.3/3.0 artifact and the final 0.4/4.0 bundle claim. See [grading-events.md Event 003](grading-events.md) for the operator-triggered change.

---

This file uses only the vocabulary established in [data-point.md](data-point.md), [collection-program.md](collection-program.md), and [pointer.md](pointer.md). No new bedrock concepts are introduced; this file is the *composition rule* over the three foundations — specifically, the rule the **0.4 protocol** uses to compose 1.0 + 2.0 + 3.0 components into a **4.0 bundle**.

## What 4.0 is (positive definition)

A **4.0 bundle** is a directory containing:

1. **1.0 layer (collectors produced under 0.1).** One or more collection programs (Foundation 2), each with its declared `collector_id`, `kind`, `value_schema`, `inputs`. The data points (Foundation 1) those collectors have produced, persisted in a data-point store under their `id`s. A pointer-resolver collector for every pointer kind referenced by anything in the bundle.

2. **2.0 layer (signals produced under 0.2).** One or more *signals*. A signal is a 2.0 program: a deterministic function whose input is a fixed shape (typically a candidate the 3.0 orchestration is considering) and whose output is `(verdict, confidence, evidence_pointers)`. A signal's parameters — thresholds, frequency tables, learned weights, decision rules — are *fitted* to a dataset, not authored. The dataset is a set of data points produced by 1.0 collectors. Each signal carries a manifest entry naming its training-dataset pointers.

3. **3.0 layer (orchestration produced under 0.3).** Orchestration source. A 3.0 program (or set of programs) that, when invoked, walks declared 1.0 inputs, queries declared 2.0 signals at declared decision points, and emits a *candidate artifact*. Every consultation is logged with the consulted fence and its result.

4. **Manifest.** A `manifest.json` listing every component in the bundle as a record carrying:
   - the component's role (`collector` | `signal` | `orchestration` | `dataset` | `denylist` | `output`),
   - a pointer (Foundation 3) to its source,
   - for collectors and signals, pointers to every dependency they declared,
   - for the bundle's emitted artifact, pointers to every fence the orchestration consulted while producing it.

5. **`verify.py`.** A self-contained 1.0 collector (subject to Foundation 2) that walks the manifest, runs the grading procedure below, and exits 0 iff the bundle conforms to this file. `verify.py` does not call a language model; it does not author judgement; it walks structure and reports.

6. **Emission gate.** A declared *emission-readiness signal* (a 2.0 signal) whose verdict gates whether the bundle is permitted to claim 4.0 status or only sub-4.0-candidate status. The gate's verdict is itself recorded in the manifest as a structured record (verdict + confidence + evidence_pointers).

A bundle that satisfies all six and whose `verify.py` exits 0 is a **4.0 bundle**. Anything else is, at best, a 4.0 candidate.

## The grading procedure

`verify.py` runs the following algorithm. Every step is deterministic; there is no model in the loop. Failure of any step results in non-zero exit and a structured failure record naming the failing component and the violation class.

```
1. Load manifest.json. Validate schema. Reject if malformed.

2. For each entry of role "collector":
   2a. Resolve its source pointer. Reject if dangling.
   2b. Resolve the collector's validation receipt or validator file.
       Reject the final bundle claim if neither exists or if the receipt is
       stale against the collector source_state.
   2c. When no current receipt exists, run the Foundation-2 validator on
       the resolved source:
       - declared collector_id, kind, value_schema, inputs, collect, verify
       - audit budget
       - LLM-SDK denylist (consulting data points, not prose)
       - nondeterminism scan
   2d. Run the collector twice in clean environments at the same source_state.
       Diff outputs. Reject on non-empty diff.
   2e. Emit or refresh one self-check data point per collector: pass/fail.

3. For each entry of role "dataset":
   3a. Resolve every pointer in the dataset. Reject if any dangle.
   3b. Resolve the dataset validation receipt. If it is current, record it
       and continue; do not re-derive the dataset inline.
   3c. When no current receipt exists, for each data point referenced:
       - Validate Foundation-1 schema conformance.
       - Re-derive against its provenance.source_state via its collector's
         collect(). Reject on value/witness mismatch.
   3d. Emit or refresh one self-check data point per dataset: pass/fail.

4. For each entry of role "signal":
   4a. Resolve its source pointer. Reject if dangling.
   4b. Resolve every training-dataset pointer. Reject if any dataset's
       step-3 self-check failed.
   4c. Resolve the signal's validation receipt or probe-runner file. Reject
       the final bundle claim if neither exists or if the receipt is stale.
   4d. When no current receipt exists, run the signal on a declared probe set (small fixed inputs whose
       expected outputs are themselves data points). Reject on mismatch.
   4e. Emit or refresh one self-check data point per signal: pass/fail.

5. For each entry of role "orchestration":
   5a. Resolve its source pointer. Reject if dangling.
   5b. Inspect the orchestration's declared decision points. For each
       decision point, verify that the source consults a declared 1.0
       collector or 2.0 signal at that point (structural check on the
       source — it is short enough to make this check tractable; if not,
       it violates the orchestration audit budget below).
   5c. For the bundle's emitted artifact, walk the orchestration log.
       Verify every claim in the artifact carries a pointer back to the
       fence consultation that produced it.
   5d. Emit one self-check data point per orchestration: pass/fail.

6. Run the emission-readiness signal on the bundle. Record its verdict +
   confidence + evidence_pointers. If verdict != "ready", verify.py
   still exits 0 *as a sub-4.0 candidate verification* — but the bundle
   is barred from claiming 4.0 status. The manifest's claim flag is set
   to "candidate", not "4.0".

7. For every pointer anywhere in the bundle, re-resolve at the current
   source_state. Record live/dangling. If any pointer the manifest
   marked "load-bearing" is dangling, reject.

8. Aggregate. If steps 2-5 and 7 all passed:
   - And step 6's verdict was "ready": exit 0, emit manifest claim "4.0".
   - And step 6's verdict was not "ready": exit 0, emit manifest claim
     "candidate", with the specific gap recorded.
   Otherwise: exit non-zero, emit a structured failure record.
```

The grading procedure is the algorithm. `verify.py`'s job is to execute it; everything else in the bundle is in service of giving `verify.py` something tractable to walk. The 0.4 protocol *is* this grading procedure plus the composition rule that produces something for it to walk.

The walker validates final claims, not every piece of historical production work. Lower layers are validated independently by their own files and receipts; the bundle-level walker consumes those receipts, refreshes them only when absent or stale, and then decides the strongest honest claim for the produced artifact. A stale or missing 0.1/0.2 receipt blocks a final `4.0` claim for a bundle that depends on it, but it does not block candidate emission or unrelated floor growth.

## Negative definition (what disqualifies a candidate)

A bundle is **not** 4.0 if any of the following hold. Each is a single, mechanically-detectable predicate on the bundle.

| Disqualifier | Detection |
| --- | --- |
| Any 1.0 collector lacks a current validation receipt and fails the Foundation-2 validator when refreshed | Step 2b-2d above. |
| Any data point lacks a current dataset receipt and fails re-derivation against its recorded source_state when refreshed | Step 3b-3c above. |
| Any 2.0 signal's parameters were *authored* (not fitted to a dataset of data points produced by 1.0 collectors) | Step 4b above (no training-dataset pointer that resolves to a 1.0-collected dataset = author-fit signal = reject). |
| Any 2.0 signal lacks a current validation receipt and fails its probe set when refreshed | Step 4c-4d above. |
| Any 3.0 decision point free-writes outside its declared fences | Step 5b above (structural inspection of orchestration source). |
| Any claim in the emitted artifact lacks a pointer back to the fence that produced it | Step 5c above. |
| Any load-bearing pointer dangles | Step 7 above. |
| `verify.py` itself violates Foundation 2 (imports an LLM SDK, exceeds audit budget, etc.) | `verify.py` is itself a 1.0 collector and is run through the same validator at bundle-level boot. A self-grading walker that lies is a dead bedrock. |
| The bundle's manifest describes components that do not exist on disk | Pointer-resolution fails on load. |
| The bundle declares a "4.0" claim while the emission-readiness signal returned not-ready | Step 6 above; manifest claim is forcibly downgraded to "candidate". |
| The bundle has no emission-readiness signal at all | Step 6 cannot run; reject as missing required structure. |

The asymmetry to notice: failing the emission-readiness signal does *not* invalidate the bundle as engineering — it just downgrades the claim. The same non-blocking shape applies to stale lower-layer receipts: they are reasons a final 4.0 claim cannot be stamped yet, not reasons to stop producing candidates, datasets, probes, proposals, or sibling harness work. A sub-4.0 candidate with all required files present and its validation gaps recorded is still a real artifact; it simply cannot stamp itself "4.0" until the signal and receipts say the conditions are met. This is what makes "0.4 emits 4.0 only when 2.0 signals fire" operational: the request can produce a candidate, but only the signal can promote it.

## Chosen inter-protocol wiring

Per CLAUDE.md, the wiring between adjacent protocols is *domain-determined* — not a uniform prescription. Here is the wiring chosen for the leashes built under this experiment. These patterns are the wiring, not the bedrock; a future leash for a domain that genuinely demands a different pattern can choose a different one and explicitly log the choice.

### Candidate-1.0 → graduated 1.0 (the 0.1 protocol's gate)

A 0.0 candidate-1.0 (a freshly-drafted collection program) becomes a graduated 1.0 collector when fenced by:
- a declared **schema** (the shape of valid output),
- a deterministic **validator** that runs against the schema and rejects malformed inputs,
- a non-empty **sample** of inputs the validator passes on (the sample itself is a data point produced by a sample-collector).

Generation under this fence: a 3.0 process may produce candidate output, but it is rejected unless the validator passes. A schema with no validator, or a validator with no sample, or a sample with no source — none of those is a fence. All three together are.

### 1.0 → 2.0 (the 0.2 protocol's gate)

A 2.0 signal's parameters are fitted to a *dataset*: a collection of same-kind data points conforming to a single value_schema, all produced by 1.0 collectors. The signal's manifest entry MUST declare:
- a pointer to the training-dataset (resolves to a 1.0-collected dataset),
- the fitting procedure as a deterministic 1.0 program (so refitting is reproducible),
- a *probe set*: a small fixed set of inputs whose expected outputs are recorded as data points, so `verify.py` can check the signal still does what it did at fit-time.

A signal whose training-dataset pointer dangles, or whose probe set fails on re-run, is not a valid 2.0 signal.

### 2.0 → 3.0 (the 0.3 protocol's gate)

A 2.0 signal exposes a single typed entry point: `signal.evaluate(input) -> (verdict, confidence, evidence_pointers)`.

- `verdict` is drawn from a closed enum the signal declares.
- `confidence` is a value in [0, 1] (or another bounded scale the signal declares).
- `evidence_pointers` is a list of pointers (Foundation 3) to data points whose presence in the training dataset most strongly influenced this verdict.

3.0 orchestration is required to:
- Declare its decision points up front (where in its own source it will consult signals).
- Call exactly the declared signals at exactly the declared decision points (structural check).
- Include the full `(verdict, confidence, evidence_pointers)` of each consultation in the emitted artifact's log.
- Branch on the verdict via a closed match — no fall-through, no silent ignore.

A 3.0 program that consults a signal but ignores its verdict is operating outside its 0.3-protocol fence; that is a violation, not a judgement call.

### 3.0 → 4.0 (the 0.4 protocol's gate)

A 3.0 emission becomes a 4.0 bundle only when:
- The orchestration's emission step writes a `manifest.json` enumerating every component depended on (collectors, datasets, signals, orchestration source itself, the emitted artifact).
- Lower-layer 0.1 and 0.2 validators or receipts exist for the collectors, datasets, and signals the bundle depends on.
- The emission-readiness signal is consulted as the final fence and its verdict + confidence + evidence_pointers are recorded.
- `verify.py` exits 0 with the "4.0" claim flag set.

If the emission-readiness signal returned not-ready, or if a lower-layer receipt is missing/stale, the bundle is emitted as a candidate, the manifest's claim flag is "candidate", and the gap is recorded. The candidate is a legitimate output of the 3.0 layer — just not a 4.0 output.

## The orchestration audit budget

For step 5b's structural check on orchestration to be tractable, 3.0 orchestration source files are subject to an audit budget similar to (but looser than) Foundation 2's collector budget:

- A single orchestration entry point: at most one screenful of substantive code (target ≤ 150 lines excluding imports, schema, and tests).
- Decision points declared as a top-level constant (a list of `(decision_id, fence_id)` pairs) so the structural check is a one-pass scan.
- No dynamic dispatch over fences (no "look up the signal by name from a string at runtime" without that name appearing in the declared decision-points list).

Helpers are allowed but must themselves be small enough to inspect. An orchestration entry point that grows past the budget is split into two declared-and-pointed leashes, not refactored into a black box.

## The 2.0-signals-drive-4.0 rule, made operational

CLAUDE.md says: "0.4 emits 4.0 only when 2.0 signals fire. The 0.4 protocol does not produce a 4.0 because someone asked for one."

This is realized by the **emission-readiness signal**: a 2.0 signal each leash is required to declare. Its job is to look at the dataset coverage, the strength of the signals consulted during this run, and the candidate the 3.0 orchestration is about to emit, and return:

- `("ready", confidence, evidence_pointers)` when the signal's training data covers the situation densely enough and the bundle's checks all came back strong, OR
- `("not_ready", confidence, evidence_pointers, gap_record)` when coverage is thin, signals were borderline, or some declared check returned weak — `gap_record` names what specifically is missing.

A first-run leash, by construction, has a thin training dataset and weak signals. The honest verdict is `not_ready`, the bundle is a candidate, and `gap_record` says exactly what would have to grow for the next run to be ready. This is how floor-growth becomes measurable: the gap_record from run N is the input to what the 1.0 layer must collect more of before run N+1 can claim 4.0.

## Sub-4.0 candidate is a real output

A bundle whose `verify.py` exits 0 with claim "candidate" is *not* a failure. It is a legitimate output of the 3.0 layer that has done all the engineering 4.0 requires *except* that the dataset is too thin for the emission-readiness signal to fire. Every collector ran, every data point re-derived, every pointer resolved live, every signal's probe set passed, every orchestration decision was logged with its consulted fence. The bundle is engineered; it just isn't yet 4.0.

This distinction matters because:
- It prevents the "fail to emit anything" trap. A leash on its first run still produces a candidate, and the candidate is the input the 1.0 layer needs to grow against.
- It prevents the "emit a fake 4.0" trap. A candidate is honest about what it isn't.
- It makes floor-growth visible round-over-round. Run 1 candidate → run 2 candidate or 4.0 → if 4.0, the floor grew enough to flip the gate; if still candidate, the gap_record names what's still missing.

## What this file does NOT specify (intentional, deferred)

- **Per-domain `kind` taxonomies.** Each leash declares its own kinds (e.g. `hook_config`, `slash_command_decl`, `claude_md_section`). This file says nothing about what kinds exist; it only requires that each is fixed once.
- **Persistence format for the data-point store.** JSON, sqlite, jsonl — the choice is per-leash. Foundation 1's shape is the constraint, not the storage.
- **Specific signal families.** The first leash uses small statistical 2.0 signals (frequency tables, threshold rules) because the data is thin and the dimensionality is low. Future leashes may use richer 2.0 families if their dataset and dimensionality justify it. The constraint is the typed query interface, not the model class.
- **The form of the emitted artifact.** A leash for hooks emits a settings.json fragment. A leash for slash commands emits a SKILL.md. A leash for CLAUDE.md emits an overlay. The artifact shape is per-domain; the manifest + verify.py contract is universal.

## Why this composition rule

Each piece exists to close a specific failure mode at the *bundle* level (the foundations close failure modes at the *primitive* level):

- The manifest closes *implicit dependency*. A bundle that doesn't enumerate what it depends on is a bundle whose dependencies cannot be re-resolved later.
- `verify.py` as a 1.0 collector closes *self-grading without a fence*. The walker is held to the same standard as the things it walks.
- The emission-readiness gate closes *vibes-driven 4.0*. A request-driven emission is a 0.0 free-write dressed up; a signal-driven emission is one where the bedrock decided.
- The candidate-vs-4.0 distinction closes the *all-or-nothing trap*. First-run leashes can emit something legitimate while the floor grows toward what 4.0 actually requires.
- The chosen inter-protocol wiring closes *unconstrained generation*. 3.0 has fences at every adjacent protocol; the fences are typed, runnable, and inspectable.

Holding all of these at once is what lets a 4.0 bundle be walked by a 3.0 running 0.4 and verified — which is what CLAUDE.md says is the litmus: "If a 3.0-under-0.4 cannot walk it, it is not 4.0."
