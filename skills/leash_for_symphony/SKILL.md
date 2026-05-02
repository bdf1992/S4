---
name: leash-for-symphony
description: Generate a chain-disciplined proposal for a Symphony WORKFLOW.md file (the per-repo configuration consumed by openai/symphony and its forks, e.g. hawkymisc/cc-symphony). Walks the operator's candidate WORKFLOW.md corpus, fits two 2.0 signals (symphony_permission_posture, emission_readiness) on the resulting datasets, runs the candidate through three declared decision points, and emits a bundle directory containing the candidate WORKFLOW.md plus a manifest enumerating every component depended on. The leash carries the standard three-position toggle (on/off/scoped) read from `leash_state.json`, plus an orthogonal `vocal` boolean that forces full structured-event capture into the bundle regardless of toggle state. First non-Claude-Code-surface leash; built under an explicit override_record (see proposals/prop_2026-04-30_leash-for-symphony/override_record.md). Imports the bedrock validators and shared resolvers/signals from leash_for_hooks (round-3 reuse). Built bottom-up under foundations/{data-point, collection-program, pointer, zero-four}.md.
when_to_use: When the operator wants a Symphony WORKFLOW.md proposal verified against the upstream SPEC's field taxonomy, against the operator's existing WORKFLOW corpus for permission-posture drift, and against the bedrock chain before shipping the file to a Symphony runtime. Defaults to read-only verification; only writes a bundle directory under outputs/ and (on candidate emission) a proposal under exemplars/proposed/. Do NOT use to edit an in-flight Symphony deployment — the leash produces *proposals*, not edits, and never invokes Symphony at runtime.
argument-hint: "[run|verify] [<candidate.json>|<bundle_dir>]"
allowed-tools: Bash, Read
---

<!-- Frontmatter conforms to the Anthropic Agent Skill spec
     (https://code.claude.com/docs/en/skills, verified 2026-04-29).
     Surface, category, and pattern are captured in the body line below
     because the spec has no metadata block — same convention as
     leash-for-hooks and leash-for-slash-commands. -->

> **About this skill** — surface: `symphony-workflow-md` · rides under: Claude Code · category: harness-control · pattern: chain-disciplined-leash. License: MIT.

# leash-for-symphony

A leash for the Symphony `WORKFLOW.md` configuration surface. When invoked with a candidate WORKFLOW.md (parsed YAML front matter + body), this skill walks the bedrock chain bottom-up — 1.0 collectors under 0.1 → 2.0 signals under 0.2 → 3.0 orchestration under 0.3 — and emits a bundle that is either a 4.0 program or, more honestly on first-run thin data, a 4.0 candidate.

This skill is the **third** leash in the experiment, and the **first to target a surface outside Claude Code itself**. The structural novelty is logged in [proposals/prop_2026-04-30_leash-for-symphony/README.md](../../proposals/prop_2026-04-30_leash-for-symphony/README.md); the override of the recursion-seam's outcome-5 gate (which expects accumulated hand-walks before a sibling leash is built) is logged in [proposals/prop_2026-04-30_leash-for-symphony/override_record.md](../../proposals/prop_2026-04-30_leash-for-symphony/override_record.md).

Symphony's SPEC §10.5 *requires* every implementation to document its chosen approval, sandbox, and operator-confirmation posture. Filling that slot — leashed or not, vocal or not — is conformant adapter behavior, not an override of upstream Symphony. This skill produces the artifact (the WORKFLOW.md file) that fills it.

## Inputs

`$ARGUMENTS`:

- `run [<candidate.json>]` — execute the orchestration. With no argument, uses `DEFAULT_CANDIDATE` (a low-risk WORKFLOW.md with `claude.skip_permissions: false` and `tracker.kind: github`). With a JSON file path, reads the candidate from disk. Writes a bundle to `outputs/run-<hash>/`.
- `verify [<bundle_dir>]` — run the grading procedure. With no argument, verifies the skill bundle itself. With a bundle directory, also verifies that emitted bundle.

If absent, defaults to `verify`.

## Bedrock pointers

This skill is a concrete third instance of [foundations/zero-four.md](../../foundations/zero-four.md). It does **not** reimplement the bedrock; it imports it.

### Imported verbatim from leash_for_hooks (no copy)

These are the floor — what makes round 3 cheaper than round 1:

- [skills/leash_for_hooks/lib/data_point.py](../leash_for_hooks/lib/data_point.py) — Foundation 1.
- [skills/leash_for_hooks/lib/collection_program.py](../leash_for_hooks/lib/collection_program.py) + [lib/audit.py](../leash_for_hooks/lib/audit.py) — Foundation 2.
- [skills/leash_for_hooks/lib/pointer.py](../leash_for_hooks/lib/pointer.py) — Foundation 3.
- [skills/leash_for_hooks/lib/leash_state.py](../leash_for_hooks/lib/leash_state.py) — operator-authored toggle. The shared validator first-classes the orthogonal `vocal` field (must be bool if present) and exposes `is_vocal(d)` for polymorphic reads against state-shaped or outcome-shaped dicts; lift completed 2026-04-30 once the leash-for-cc-afk preview made it the second leash to want the shape.
- [skills/leash_for_hooks/collectors/llm_sdk_denylist.py](../leash_for_hooks/collectors/llm_sdk_denylist.py) — recursive LLM-SDK fence.
- [skills/leash_for_hooks/resolvers/file_line.py](../leash_for_hooks/resolvers/file_line.py), [collector.py](../leash_for_hooks/resolvers/collector.py), [data_point.py](../leash_for_hooks/resolvers/data_point.py) — universal pointer resolvers.
- [skills/leash_for_hooks/signals/emission_readiness.py](../leash_for_hooks/signals/emission_readiness.py) — the 2.0-signals-drive-4.0 gate.

Per [recursion-seam.md:83](../leash_for_hooks/recursion-seam.md#L83), three siblings is the threshold for de-duplication. This is the third sibling. The lift to a top-level `bedrock/` package is on the followup list (the existing `slash_commands` skill imports from `leash_for_hooks` too; this skill does the same and the lift coordinates all three siblings in one move).

### New for this surface (the seams)

| File | Role | Analog in leash_for_hooks |
| --- | --- | --- |
| [references/symphony-workflow-fields.txt](references/symphony-workflow-fields.txt) | field-name taxonomy | references/hook-events.txt |
| [collectors/symphony_field_decl.py](collectors/symphony_field_decl.py) | walks taxonomy | collectors/hook_event_decl.py |
| [collectors/symphony_workflow.py](collectors/symphony_workflow.py) | walks WORKFLOW.md corpus | collectors/hook_config.py |
| [collectors/exemplar_bundle_state.py](collectors/exemplar_bundle_state.py) | walks own promoted dir | collectors/exemplar_bundle_state.py |
| [signals/symphony_permission_posture.py](signals/symphony_permission_posture.py) | posture-drift check | signals/hook_collision.py |
| [orchestrate.py](orchestrate.py) | 3.0 entry point + vocal capture wiring | orchestrate.py |
| [verify.py](verify.py) | 4.0 grading walker | verify.py |
| [leash_state.json](leash_state.json) | toggle state + `vocal` field | leash_state.json |

## The chain, by file

### 1.0 layer (under 0.1)

| Collector | KIND emitted | Source walked |
| --- | --- | --- |
| [skills/leash_for_hooks/collectors/llm_sdk_denylist.py](../leash_for_hooks/collectors/llm_sdk_denylist.py) | `llm_sdk_denylist_entry` | [foundations/llm-sdk-denylist.txt](../../foundations/llm-sdk-denylist.txt) |
| [collectors/symphony_field_decl.py](collectors/symphony_field_decl.py) | `symphony_field_decl` | [references/symphony-workflow-fields.txt](references/symphony-workflow-fields.txt) |
| [collectors/symphony_workflow.py](collectors/symphony_workflow.py) | `symphony_workflow` | [datasets/workflow-corpus/*.json](datasets/workflow-corpus/) — operator-committed pre-parsed WORKFLOW.md front-matter dicts; JSON-shaped to keep parsing deterministic and stdlib-only. May be empty on first run. |
| [collectors/exemplar_bundle_state.py](collectors/exemplar_bundle_state.py) | `exemplar_bundle_state` | [exemplars/promoted/*.json](exemplars/promoted/) |

### 2.0 layer (under 0.2)

| Signal | Fitted on (training-dataset KIND) | Verdict enum |
| --- | --- | --- |
| [signals/symphony_permission_posture.py](signals/symphony_permission_posture.py) | `symphony_workflow` | `posture_consistent`, `posture_drift` |
| [skills/leash_for_hooks/signals/emission_readiness.py](../leash_for_hooks/signals/emission_readiness.py) | `exemplar_bundle_state` | `ready`, `not_ready` |

### 3.0 layer (under 0.3)

[orchestrate.py](orchestrate.py) — declared `DECISION_POINTS`:

```python
DECISION_POINTS = [
    ("workflow_field_validity",   "symphony_field_decl"),         # 1.0 dataset membership
    ("permission_posture_check",  "symphony_permission_posture"), # 2.0 signal
    ("emission_gate",             "emission_readiness"),          # 2.0 shared signal
]
```

**Surface-specific subtlety:** `workflow_field_validity` is a *membership* check (every front-matter key in the candidate must appear in the taxonomy dataset; unknown keys reject). This matches the polarity of `event_validity` in leash_for_hooks (membership) and inverts the polarity of `name_validity` in leash_for_slash_commands (non-membership against reserved names).

### Toggle gate, with vocal-mode extension

Before `DECISION_POINTS` runs, the standard `toggle_check` consults [leash_state.json](leash_state.json) via [skills/leash_for_hooks/lib/leash_state.py](../leash_for_hooks/lib/leash_state.py). Because the shared validator silently accepts extra fields, this skill reads the orthogonal `vocal` boolean directly.

| `state` | `vocal` | Effect |
| --- | --- | --- |
| `on` | any | Surface decisions consulted; bundle records every step. |
| `off` | `false` | Candidate passes through; claim `unleashed`; minimal log. |
| `off` | `true` | Candidate passes through; claim `unleashed`; **full structured-event log emitted regardless** — toggle gate logs the `vocal=true` choice, and orchestrate writes a `vocal_capture_plan.md` into the bundle that wires `hooks.after_run` in the candidate WORKFLOW.md to pipe Symphony's per-run event stream into this skill's `outputs/<run-id>/symphony-events.jsonl`. |
| `scoped` | any | Per-event toggle; `vocal` honored if scoped-on. |

The default committed value is `{"state": "off", "vocal": true}` per [proposals/prop_2026-04-30_leash-for-symphony/README.md](../../proposals/prop_2026-04-30_leash-for-symphony/README.md): the operator has trust-established Symphony as autonomous (state=off) but wants every choice the autonomous run makes captured loudly (vocal=true).

### 4.0 layer (under 0.4)

[verify.py](verify.py) — same shape as [skills/leash_for_hooks/verify.py](../leash_for_hooks/verify.py) and [skills/leash_for_slash_commands/verify.py](../leash_for_slash_commands/verify.py). Baseline self-checks against the skill bundle; +N self-checks per output bundle passed as argument. An additional `vocal_capture` self-check confirms that when `state=off` and `vocal=true`, orchestrate wrote the `vocal_capture_plan.md` artifact.

## Operating loop

1. **`run`** — execute orchestrate, write `outputs/run-<hash>/{manifest.json, candidate.json, orchestration-log.jsonl}`. If `claim=candidate`, also write `exemplars/proposed/<run>.json`. If `vocal=true`, additionally write `outputs/run-<hash>/vocal_capture_plan.md` describing the `hooks.after_run` shim the operator should add to the candidate WORKFLOW.md to pipe Symphony events back here.
2. **`verify`** — run baseline self-checks; if a bundle dir is given, also check claim consistency, decision-point ordering, and (when `vocal=true`) presence of `vocal_capture_plan.md`.

## Levels

- **v0.1 (current)** — manual run/verify. First-run candidates only; corpus is empty (the operator has no committed WORKFLOW.md candidates yet); `symphony_permission_posture` is fitted on nothing and emits `posture_consistent` with confidence 0. No 4.0 emissions because the exemplar dataset is empty (0/`MIN_EXEMPLARS`). The override_record explicitly forbids upgrading any v0.1 bundle to `4.0` regardless of seam-state.
- **v0.2** — exemplar accretion + WORKFLOW corpus growth. Once the operator commits real WORKFLOW.md candidates under [datasets/workflow-corpus/](datasets/workflow-corpus/) and promotes exemplar bundles, both signals get sharper.
- **v0.3** — bedrock lift. With three sibling leashes now extant, lift `lib/`, `resolvers/`, `collectors/llm_sdk_denylist.py`, `signals/emission_readiness.py` from `leash_for_hooks/` to a top-level `bedrock/` package and repoint all three siblings.

## Files

- [SKILL.md](SKILL.md) — this file.
- [verify.py](verify.py) — the 4.0 grading walker.
- [orchestrate.py](orchestrate.py) — the 3.0 entry point.
- [leash_state.json](leash_state.json) — the operator toggle. Default: `{"state": "off", "vocal": true}` per the proposal.
- [collectors/](collectors/) — three surface-specific collectors.
- [signals/symphony_permission_posture.py](signals/symphony_permission_posture.py) — surface-specific signal.
- [references/symphony-workflow-fields.txt](references/symphony-workflow-fields.txt) — WORKFLOW.md field taxonomy (commit-pinned snapshot of upstream + cc-symphony fork).
- [datasets/](datasets/) — collector outputs (regenerable; written by `run`).
- [datasets/workflow-corpus/](datasets/workflow-corpus/) — operator-committed WORKFLOW.md candidates. May be empty.
- [outputs/](outputs/) — emitted bundles, one per run (regenerable).
- [exemplars/proposed/](exemplars/proposed/) — bundles awaiting human promotion.
- [exemplars/promoted/](exemplars/promoted/) — promoted exemplars; the `emission_readiness` training corpus.
