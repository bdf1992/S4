# orchestration_audit

A skill whose only job is to measure 0.3 from beneath, by walking the artifacts that 0.3 orchestrations write while running, and turning them into Foundation-1 data points.

## Why this exists

The orchestration log every leash and audit emits — `skills/*/outputs/run-*/orchestration-log.jsonl` — is **0.3 self-report**, not a 0.1 dataset. An independent 0.1 collector that walks those logs and re-derives the same data points across runs converts self-report into measurement. Without that conversion, any 0.2 signal trained on the logs would be fitting an LLM-adjacent corpus and would invert the bedrock direction (0.2 leaning on 0.3 instead of the reverse).

## What's here

- [collectors/orchestration_activations.py](collectors/orchestration_activations.py) — **Prereq A.** Walks every run's orchestration-log.jsonl, attaches the run's manifest claim as run-level context, emits one `orchestration_activation` data point per logged consultation. Run via `python -m skills.orchestration_audit.collectors.orchestration_activations`.
- [collectors/decision_point_honesty.py](collectors/decision_point_honesty.py) — **Prereq B.** For each `(skill_id, decision_id, fence_id)` tuple seen in the activations corpus, measures: where the literals appear in `skills/{skill_id}/**/*.py`, branch and verdict diversity observed across runs, and which branches were taken under which verdicts. Reports measurements only; honesty classification belongs to a downstream signal. Run via `python -m skills.orchestration_audit.collectors.decision_point_honesty`.
- [datasets/orchestration_activations.jsonl](datasets/orchestration_activations.jsonl), [datasets/decision_point_honesty.jsonl](datasets/decision_point_honesty.jsonl) — collector outputs. Regenerable; not authoritative; gitignored.
- [lib/data_point.py](lib/data_point.py) — local Foundation-1 wrapper (per-consumer copy; see debt D-001).

## What's *not* here yet (deferred)

- **Trace-conformity 0.2 model implementation.** Architecture is committed at [0_2_design.md](0_2_design.md): a probabilistic finite-state machine over the trace, with shared decision-id embeddings, edge weights parameterized per `(fence_id, verdict, branch_taken)`, per-skill linear heads, gradient-fit on trace likelihood, leave-one-run-out cross-validation. The doc names what is committed and what is deferred to implementation, plus the corpus gaps that prevent `verdict=ready` from firing today (zero `claim:0.4` runs, 9 of 12 tuples monotone). Implementation step is a clean punch list.
