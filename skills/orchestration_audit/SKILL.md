# orchestration_audit

A skill whose only job is to measure 0.3 from beneath, by walking the artifacts that 0.3 orchestrations write while running, and turning them into Foundation-1 data points.

## Why this exists

The orchestration log every leash and audit emits — `skills/*/outputs/run-*/orchestration-log.jsonl` — is **0.3 self-report**, not a 0.1 dataset. An independent 0.1 collector that walks those logs and re-derives the same data points across runs converts self-report into measurement. Without that conversion, any 0.2 signal trained on the logs would be fitting an LLM-adjacent corpus and would invert the bedrock direction (0.2 leaning on 0.3 instead of the reverse).

## What's here

- [collectors/orchestration_activations.py](collectors/orchestration_activations.py) — **Prereq A.** Walks every run's orchestration-log.jsonl, attaches the run's manifest claim, emits one `orchestration_activation` data point per logged consultation. (54 records.)
- [collectors/decision_point_honesty.py](collectors/decision_point_honesty.py) — **Prereq B.** For each `(skill_id, decision_id, fence_id)` tuple seen in the activations corpus, measures source-presence and branch/verdict diversity. Reports measurements only; honesty classification belongs to the signal. (12 records.)
- [collectors/pfsm_parameters.py](collectors/pfsm_parameters.py) — **0.2 model fit.** Deterministic SGD over a feature-bag linear softmax classifier (skill one-hot + decision counts + fence counts + bias), 500 iterations, fixed seed via SHA-256 expansion. Emits one `pfsm_parameters` data point containing fitted weights, classes, hyperparameters, training_runs, and final_loss.
- [signals/trace_conformity.py](signals/trace_conformity.py) — **0.2 signal.** Loads `pfsm_parameters` and exposes `evaluate(trace) -> {verdict, confidence, top_class, class_probabilities, evidence_pointers, gap_record}`. Verdict is `ready` (top class is 0.4 above threshold), `not_ready` (top class is candidate/rejected, or near-uniform softmax), or `inconclusive` (top class is a non-0.4 success class). The `gap_record` reports corpus dimensions on every non-ready emission.
- [probes/trace_conformity_probes.json](probes/trace_conformity_probes.json) — fixed probe set per [0_2_design.md](0_2_design.md): empty trace, candidate replay, aggregated replay, no-target-class corpus check.
- [verify.py](verify.py) — bundle self-check: 35 structural + behavioral checks (file presence, parse, no LLM SDK, no nondeterminism, all collector outputs verify live, PFSM parameters fresh against current corpus, every probe matches expected envelope).
- [lib/data_point.py](lib/data_point.py) — local Foundation-1 wrapper (per-consumer copy; see debt D-001).

## How to invoke

```bash
# refit collectors and PFSM at current source_state
python -m skills.orchestration_audit.collectors.orchestration_activations
python -m skills.orchestration_audit.collectors.decision_point_honesty
python -m skills.orchestration_audit.collectors.pfsm_parameters

# run the bundle's self-check
python -m skills.orchestration_audit.verify
```

## Current verdict on this corpus

The signal correctly emits `not_ready` or `inconclusive` on every probe today; `verdict=ready` is unreachable because [datasets/orchestration_activations.jsonl](datasets/orchestration_activations.jsonl) contains zero `claim:0.4` runs. Each non-ready emission carries a `gap_record` reporting `runs_with_claim_0_4_in_corpus`, `monotone_tuples` count, `runs_per_class_in_corpus` distribution, and `missing_target_class`. As corpus grows organically, the gap_record values change and the verdict can shift toward `ready` without any code change.

## What's deferred to v1

- **Per-skill linear heads** (design doc named) — v0 uses a single shared head across skills. Adding per-skill heads requires more parameters than 24 runs can fit without regularization tuning; revisit when corpus grows.
- **Real PFSM transition weights** keyed on `(fence_id, verdict, branch_taken)` triples — v0 uses bag-of-features (decision_id presence, fence_id presence) which loses sequence ordering. The honesty measurements from Prereq B are not yet used as edge-quality weights; v1 adds them as inductive bias.
- **Leave-one-run-out cross-validation reporting** — v0 fits on full corpus and reports training accuracy (1.00, expected overfit on 138 parameters / 24 runs). v1 reports held-out accuracy and macro-F1.
- **Threshold calibration for `verdict=ready`** — `READY_THRESHOLD = 0.5` is placeholder; real calibration requires at least one `claim:0.4` trace held out from training.
