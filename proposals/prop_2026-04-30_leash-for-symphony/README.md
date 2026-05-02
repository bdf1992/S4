# leash-for-symphony — design preview

**Status:** design preview, **not** a Foundation-2-verified proposal yet. See "What's missing" below.

## Operator directive

> Symphony should be leash off mode, vocal mode, and I want to do that.

This proposal records that directive as the seed for a sibling leash whose surface is OpenAI's `openai/symphony` — a queue-driven, autonomous, PR-landing harness pattern external to Claude Code. It does **not** yet build the skill bundle. It records the design choices, names the structural novelty, and gates the build on the project's documented recursion-seam.

## What's new about this surface (vs. existing leashes)

[skills/leash_for_hooks/](../../skills/leash_for_hooks/) and [skills/leash_for_slash_commands/](../../skills/leash_for_slash_commands/) target **Claude Code** surfaces — `settings.json/hooks` and `.claude/commands/*.md`. The recursion-seam in [skills/leash_for_hooks/recursion-seam.md](../../skills/leash_for_hooks/recursion-seam.md) anticipates siblings on *other Claude Code surfaces* (MCP wirings, agent definitions, CLAUDE.md sections).

Symphony is the **first surface outside Claude Code** the operator wants leashed. That has structural consequences:

- **Sub-to-host is preserved by direction, not by inheritance.** The existing leashes ride under Claude Code because they constrain Claude Code's own configuration. A Symphony leash cannot ride *under* Symphony — Symphony is a different host. Instead, the leash rides under Claude Code (the host of this skill) and *constrains the operator's emissions to* Symphony. The artifact graded is the operator's candidate `WORKFLOW.md` (Symphony's per-repo config file) before it gets shipped to a Symphony runtime — not Symphony's runtime itself.
- **Symphony's SPEC accommodates the leash as an explicit slot.** SPEC §10.5 requires every implementation to *"document its chosen approval, sandbox, and operator-confirmation posture."* That is exactly the leash, declared by the upstream spec as implementation-defined. Filling that slot is conformant adapter behavior, not an override.
- **Anti-pattern proximity (still flagged).** CLAUDE.md warns against "operating beneath the 0.0 text surface so humans simply observe the results." Symphony's pitch ("manage work instead of supervising agents") sits adjacent. Leash=off + vocal=on is the operator's chosen reconciliation: the surface is autonomous (operator does not supervise) but loud (operator can grade afterward by reading the captured event stream). This is a deliberate trust-established choice, recorded here so it is not silent.

## Forks scanned (2026-04-30)

Symphony has 18 pages of forks. Two are Claude-named and were inspected:

| Fork | Stack | Tracker | Adaptation status |
| --- | --- | --- | --- |
| [`hawkymisc/cc-symphony`](https://github.com/hawkymisc/cc-symphony) | Rust | GitHub Issues | **Full Codex → Claude Code CLI swap, all phases complete.** Exposes `skip_permissions` (default `false`) and `allowed_tools` in `WORKFLOW.md`. Workspace hooks (`after_create`, `before_run`, `after_run`, `before_remove`) present. 79 commits, active. Has its own `SPEC.md` and `SPEC_GITHUB.md`. |
| [`philipdaquin/symphony-claude`](https://github.com/philipdaquin/symphony-claude) | Elixir | Linear | Dual-runtime: adds Claude alongside Codex via `agent.adapter: claude`. Doesn't touch approval/sandbox/hooks. 15 commits. |

`cc-symphony` is the natural upstream to ride under: the Codex → Claude swap is already done, the approval/sandbox slot is already a config field, and GitHub Issues (vs. Linear) means no extra credentials surface for the operator. **This proposal targets `cc-symphony`'s `WORKFLOW.md` as the candidate artifact.** If the operator later decides to ride under upstream Symphony or `symphony-claude`, the seam-pattern transfers — the leash generates a WORKFLOW.md, the runtime is whichever fork the operator points it at.

Other forks with hint-of-divergence names (`fifony`, `rondo`, `rusty`, `symphonia`, `karkhana`, `OpenSymphony`) were not inspected. None named in a way that suggests leash-discipline work specifically. If we discover one later, the proposal can be amended.

## Operator's chosen toggle, encoded

`leash_state.json` for this surface, on first commit:

```json
{ "state": "off", "vocal": true }
```

- `state: "off"` — surface decision points are not consulted at run time. Candidates pass through; `claim` is `"unleashed"`. This is the existing on/off/scoped axis from [CLAUDE.md:127](../../CLAUDE.md#L127), set to off as the operator's prior.
- `vocal: true` — **new orthogonal field** specific to this leash. Even when `state == "off"`, the orchestration still emits the full structured report stream (decision-point consultations, evidence pointers, gap_records) into `outputs/run-<hash>/`. The leash is silent (does not gate); the bundle is loud (every choice the autonomous run made is auditable post-hoc).

`vocal` is **not a fourth toggle state** — it is orthogonal to on/off/scoped because it answers a different question. State answers "does this leash gate?" Vocal answers "does this leash narrate?" An on+silent leash gates without explaining; an off+vocal leash narrates without gating. This proposal asks for the off+vocal cell.

If `vocal` proves useful across other surfaces, lift it to [lib/leash_state.py](../../skills/leash_for_hooks/lib/leash_state.py)'s shared validator. Until a second leash needs it, keep it Symphony-local.

## Surface seams (what would change per [recursion-seam.md](../../skills/leash_for_hooks/recursion-seam.md))

Mapping the seam checklist in `recursion-seam.md` to Symphony, now grounded in the actual SPEC and `cc-symphony`'s WORKFLOW shape:

| Seam | Symphony fill |
| --- | --- |
| `references/<surface>-taxonomy.txt` | `references/symphony-workflow-fields.txt` — the closed enumeration of `WORKFLOW.md` front-matter fields (tracker.kind, polling.interval_ms, workspace.root, hooks.{after_create,before_run,after_run,before_remove}, agent.max_concurrent_agents, claude.permission_mode, claude.allowed_tools, claude.skip_permissions, etc.) sourced from upstream `SPEC.md` plus `cc-symphony/SPEC_GITHUB.md`, commit-pinned. |
| `collectors/<surface>_decl.py` | `collectors/symphony_field_decl.py` — walks the taxonomy file. Same shape as `hook_event_decl.py`. |
| `collectors/<surface>_config.py` | `collectors/symphony_workflow.py` — walks `WORKFLOW.md` candidates the operator commits to this repo (e.g. under `proposals/.../candidate/WORKFLOW.md`). Parses YAML front matter, normalizes to a `symphony_workflow` data point. On first run, corpus is empty. |
| `signals/<surface>_collision.py` | `signals/symphony_permission_posture.py` — fits over the corpus to detect candidates that drift from the operator's prior posture (e.g. a candidate that flips `skip_permissions: true` against a corpus of `false`-defaulted exemplars is flagged). Verdict enum: `posture_consistent` / `posture_drift`. |
| `signals/emission_readiness.py` | shared verbatim. `MIN_EXEMPLARS = 50` applies. |
| `orchestrate.py` `DECISION_POINTS` | `[("workflow_field_validity", "symphony_field_decl"), ("permission_posture_check", "symphony_permission_posture"), ("emission_gate", "emission_readiness")]`. |
| toggle gate | reads `leash_state.json`; honors `state` per existing semantics; additionally reads `vocal` and forces full report emission regardless of state. |

The leash candidate is a **`WORKFLOW.md` file** — the same shape Symphony itself consumes. That keeps the artifact in Symphony's native vocabulary; the operator is not learning a new format.

Bedrock-shared (imported, not reimplemented): `lib/data_point.py`, `lib/collection_program.py`, `lib/pointer.py`, `lib/audit.py`, `collectors/llm_sdk_denylist.py`, resolvers, `signals/emission_readiness.py`. Same as for any sibling leash.

## Vocal-mode capture path (now concrete)

Symphony's SPEC §10.4 enumerates the structured event types the runtime emits: `session_started`, `turn_completed`, `turn_failed`, `turn_cancelled`, `turn_input_required`, `approval_auto_approved`, `unsupported_tool_call`, `notification`, rate-limit events, token-usage updates. SPEC §13.5 specifies token accounting fields. SPEC §13.7 declares an *optional* HTTP observability API.

"Vocal mode" maps directly to capturing this stream:

- **At-emit:** the candidate `WORKFLOW.md` produced under leash=off+vocal=on includes `hooks.after_run` configured to invoke a one-line shim that pipes Symphony's per-run event log into `outputs/run-<hash>/symphony-events.jsonl` in this repo.
- **Post-run import:** the operator runs a sync command (no new infrastructure) after Symphony finishes; the leash's verifier walks the captured event stream and grades it against the bundle's manifest, the same way `verify.py` walks declared decision points.
- **Pointer integrity:** every captured event becomes a data point with provenance pinned to Symphony's `thread_id` + `turn_index`. The pointer is computed, not authored.

## What's missing to become a Foundation-2 proposal

Per [CLAUDE.md](../../CLAUDE.md): *"0.4 emits 4.0 only when 2.0 signals fire."* The recursion-seam extends this: a sibling leash gets built when a signal indicates it should, not when it is requested.

The relevant signal here is **outcome 5** in [recursion-seam.md](../../skills/leash_for_hooks/recursion-seam.md#L31): *"the operator is repeatedly applying chain discipline by hand to a surface no existing leash covers. Every time the same shape of ad-hoc verification gets re-derived, that recurrence is the signal that a new leash should formalize it."*

Status as of this writing:

- The operator has named Symphony as a target surface **once**, in this session.
- No prior session in `meeting-notes/` records a Symphony hand-walk.
- `proposals/REVIEW.md` does not yet reference Symphony.
- No `gap_audit` collector for "ad-hoc Symphony chain discipline" exists.

By the seam's own gate, a single directive is **not** a fired signal. To upgrade this design preview to a Foundation-2 proposal:

1. **Build a `surface_handwalk_recurrence` gap collector** under [skills/gap_audit/](../../skills/gap_audit/) (or its successor). It walks `meeting-notes/`, `proposals/`, and chat-transcript logs for repeated ad-hoc chain-discipline application against a named non-Claude-Code surface. Emits a `surface_handwalk` data point per occurrence, keyed by surface identifier.
2. **Wait for ≥ N occurrences against `surface=symphony`.** The threshold is the same shape as `MIN_EXEMPLARS = 50` for emission_readiness — a number that fences against single-request promotion. The exact value (3? 5? 10?) is a separate design choice, fitted to operator session cadence.
3. **Re-run this proposal** against the gap data points, with the candidate skill bundle in `candidate/`, producing `gap.json`, `pre_verification.json`, `proposal.json`.

Until step 1, this is a 0.0-stage design exercise authored by a 3.0 — useful for committing the operator's directive to an artifact, **not yet a 4.0 emission**.

## Two paths for the operator

**Path A — record the directive, build the signal first (seam-conformant):**

1. Land this README as the design preview (this commit).
2. Build the `surface_handwalk_recurrence` gap collector as the next move.
3. The collector retroactively counts this session as occurrence #1 against `surface=symphony`. Future sessions either accumulate or don't.
4. When the threshold is crossed, build `skills/leash_for_symphony/` from this preview as the candidate bundle.

**Path B — operator overrides the seam-gate by fiat (override-conformant, vocal):**

1. Land this README plus a companion `override_record.md` in this directory naming: who overrode (operator), when, against what gate (recursion-seam outcome 5), and why (Symphony is novel enough that chain-discipline-by-hand against it cannot accumulate without first having the formalization).
2. Build `skills/leash_for_symphony/` immediately as a v0 skill bundle, claim `"candidate"` (no exemplars, fresh corpus).
3. The override_record itself is a 4.0 grading event — it logs the operator deciding the rule was wrong-shaped for this case, which the existing [foundations/grading-events.md](../../foundations/grading-events.md) accommodates.

**Path A is the seam's default.** Path B is what "vocal mode" looks like applied to the apparatus's own discipline: rather than silently ignoring the gate, log the override loudly so the next operator (or a future audit) can see exactly what was done and why.

## Production placement (post-promotion, either path)

```
skills/leash_for_symphony/
├── SKILL.md                       # surface: symphony · rides under: Claude Code
├── leash_state.json               # {"state": "off", "vocal": true}
├── recursion-seam.md              # near-verbatim, with non-CC-surface notes
├── lib/                           # shared (or imported from bedrock/)
├── collectors/
│   ├── symphony_role_decl.py
│   ├── symphony_run_decl.py
│   └── llm_sdk_denylist.py        # shared
├── resolvers/                     # shared
├── signals/
│   ├── symphony_role_collision.py
│   └── emission_readiness.py      # shared
├── orchestrate.py                 # honors state + vocal
├── verify.py                      # 4.0 grading walker
├── references/
│   └── symphony-roles.txt         # taxonomy snapshot, commit-pinned
└── outputs/                       # bundles, one per autonomous Symphony run
```

## Open questions (deferred to candidate phase)

- ~~**What is "the candidate" being graded?**~~ **Resolved:** the operator's `WORKFLOW.md` file, pre-emission. Graded before Symphony executes; vocal mode makes the post-execution event stream loud independently.
- ~~**How does Symphony's report stream get back into `outputs/run-<hash>/`?**~~ **Resolved:** post-run import via a `hooks.after_run` shim configured into the candidate WORKFLOW.md. No new infrastructure.
- ~~**Does Symphony's reference implementation need to be vendored or just pointed at?**~~ **Resolved:** pointer-only. The taxonomy reference walks a commit-pinned snapshot of upstream `SPEC.md` + `cc-symphony/SPEC_GITHUB.md`.
- **What's `cc-symphony`'s actual stability?** 79 commits, "all phases complete" per fork description. Worth a deeper read of its SPEC_GITHUB.md before depending on it. *(Defer to candidate phase.)*
- **What's the right `MIN_EXEMPLARS` for the Symphony corpus?** The shared `emission_readiness` uses 50. WORKFLOW files turn over slower than hook configs; 50 may be too high. Fit it to operator cadence in candidate phase.
