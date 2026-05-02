# leash-for-cc-afk — design preview

**Status:** design preview, **not** a Foundation-2-verified proposal yet, and **not** an authorization to build the skill bundle. See "What's missing" and "Two paths" below.

## Operator directive

> let work on a tursted auto/afk mode utalizing the 0.3 and symphony for CC

Recorded verbatim (typos preserved). The directive asks for two things stacked:

- a **trusted auto/AFK mode** for Claude Code — a runtime configuration in which the operator goes away from the keyboard while the agent continues, with established trust standing in for moment-to-moment supervision;
- and to do that **utilizing the 0.3 and Symphony** — meaning, ride on the existing 3.0-under-0.3 orchestration apparatus and apply Symphony's `{state: off, vocal: true}` pattern from [proposals/prop_2026-04-30_leash-for-symphony/](../prop_2026-04-30_leash-for-symphony/) rather than inventing a new shape.

This README records the directive as the seed for a sibling leash whose surface is **Claude Code's auto-mode runtime** — the operator-controlled mode (toggled by `/auto`) under which CC accepts low-friction execution while a session runs unattended. It does **not** yet build the skill bundle.

## What's new about this surface (vs. existing leashes)

[skills/leash_for_hooks/](../../skills/leash_for_hooks/), [skills/leash_for_slash_commands/](../../skills/leash_for_slash_commands/), and [skills/leash_for_symphony/](../../skills/leash_for_symphony/) target **configuration-file surfaces** — `settings.json/hooks`, `.claude/commands/*.md`, and Symphony's `WORKFLOW.md`. Each leash's candidate is a file the operator commits to disk; the leash grades the file before it ships to its consumer (Claude Code or Symphony).

The auto/AFK surface is the **first leash for a runtime mode rather than a config file.** That has structural consequences:

- **The candidate is a session contract, not a config file.** There is no canonical CC file the operator authors to "go AFK." The operator types `/auto`, walks away, comes back. To leash that, we have to *manufacture* a candidate artifact that did not previously exist: an explicit **AFK session plan** the operator commits before going away — declaring scope, allowed tools, expected duration, success criteria, abort conditions. The leash gates the plan; the runtime obeys the plan implicitly, the same way it obeys any prompt. The leash does **not** modify CC's runtime — it produces a contract that the operator then chooses to act under.
- **The vocal capture stream is CC's own transcript.** Symphony has SPEC §10.4 enumerating its event types, and vocal mode pipes those events into the bundle via a `hooks.after_run` shim. CC has no such spec, but CC writes the session transcript to `~/.claude/projects/<workspace-hash>/<session-id>.jsonl` as a side effect of every session. Vocal capture for CC AFK is *pointing at* that transcript file post-AFK — pinning its sha256, copying or symlinking it into the bundle, and grading it against the plan. Even simpler than Symphony's: no shim, no after_run hook, the source already exists.
- **Anti-pattern proximity (still flagged).** [CLAUDE.md](../../CLAUDE.md) warns against *"Operating beneath the 0.0 text surface so humans simply observe the results."* CC's auto-mode is exactly the surface where the operator stops observing in real time. `state: off` + `vocal: true` is the operator's chosen reconciliation: the surface is autonomous (operator does not supervise) but loud (the post-session transcript is graded against the pre-session plan). Same shape as Symphony's reconciliation. The transcript-against-plan grading is what keeps "trusted" from collapsing into "unverified."

## Operator's chosen toggle, encoded

`leash_state.json` for this surface, on first commit (if/when the skill bundle is built):

```json
{ "state": "off", "vocal": true }
```

Reusing Symphony's exact cell. The directive's word "trusted" maps to `state: off`; the discipline (loud capture for post-hoc grading) maps to `vocal: true`. Per [proposals/prop_2026-04-30_leash-for-symphony/README.md](../prop_2026-04-30_leash-for-symphony/README.md): `vocal` is orthogonal to `state` (state answers "does this leash gate?", vocal answers "does this leash narrate?"), and lived Symphony-local until a second leash needed it. **This is that second leash.** That fired the lift trigger: in the same session as this preview, `vocal` was lifted into the shared validator at [skills/leash_for_hooks/lib/leash_state.py](../../skills/leash_for_hooks/lib/leash_state.py) (now first-classes the field as `bool`-or-absent and exposes `is_vocal(d)`). The lift is a pure refactor — Symphony's bundle hash (`run-178d4e60f56a64da`) is byte-identical before and after.

## Surface seams (what would change per [recursion-seam.md](../../skills/leash_for_hooks/recursion-seam.md))

Mapping the seam checklist to CC AFK, parallel to the Symphony mapping:

| Seam | CC-AFK fill |
| --- | --- |
| `references/<surface>-taxonomy.txt` | `references/afk-plan-fields.txt` — closed enumeration of AFK plan front-matter fields (scope.allowed_paths, scope.disallowed_paths, tools.allowed, tools.disallowed, duration.expected_minutes, abort.on_first_error, abort.on_unknown_tool, success.must_produce_files, success.must_pass_command, capture.transcript_path). Sourced from this proposal as v0; commit-pinned. |
| `collectors/<surface>_decl.py` | `collectors/afk_plan_decl.py` — walks the taxonomy file. Same shape as `hook_event_decl.py` and `symphony_field_decl.py`. |
| `collectors/<surface>_config.py` | `collectors/afk_plan.py` — walks `.claude/afk-plans/*.md` candidates the operator commits. Parses YAML front matter, normalizes to an `afk_plan` data point. On first run, corpus is empty (same as Symphony's). |
| `collectors/<surface>_transcript.py` *(new seam, AFK-specific)* | `collectors/cc_session_transcript.py` — walks `~/.claude/projects/<workspace-hash>/<session-id>.jsonl` for a referenced session id. Emits a `cc_session_event` data point per turn with provenance pinned to `(session_id, turn_index)`. This is the vocal-mode source. **Symphony does not have an analog because Symphony's events come from a runtime not under CC; CC AFK's events come from CC's own state.** |
| `signals/<surface>_collision.py` | `signals/afk_scope_drift.py` — fits over the corpus to detect candidates that drift from the operator's prior posture (e.g. a candidate that opens `tools.allowed` to `Bash(*)` against a corpus of narrowly-scoped exemplars is flagged). Verdict enum: `posture_consistent` / `posture_drift`. Same polarity as Symphony's `permission_posture`. |
| `signals/scope_violation.py` *(new seam, AFK-specific)* | fits over `cc_session_event` rows against the plan's `scope` block; emits `in_scope` / `out_of_scope` per event. This is the **post-hoc grader** that vocal mode makes loud — what the operator reads when they come back. |
| `signals/emission_readiness.py` | shared verbatim. `MIN_EXEMPLARS = 50` applies. |
| `orchestrate.py` `DECISION_POINTS` | `[("plan_field_validity", "afk_plan_decl"), ("scope_posture_check", "afk_scope_drift"), ("emission_gate", "emission_readiness")]` for the **pre-AFK** path. A second orchestration entry, `grade_session(session_id, plan_id)`, runs the **post-AFK** path: walks the transcript, fits `scope_violation`, emits a session-grading bundle. |
| toggle gate | reads `leash_state.json`; honors `state` per existing semantics; reads `vocal` and forces full transcript capture into the bundle regardless of state. |

The leash candidate is a **`.claude/afk-plans/<name>.md` file** — a markdown file with YAML front matter, the same shape Claude Code already uses for slash commands, agents, and skills. The operator is not learning a new format; they are authoring one more of an existing kind.

Bedrock-shared (imported, not reimplemented): `lib/data_point.py`, `lib/collection_program.py`, `lib/pointer.py`, `lib/audit.py`, `collectors/llm_sdk_denylist.py`, resolvers, `signals/emission_readiness.py`. Same as for any sibling leash. Round-4 reuse.

## Two-phase orchestration (the AFK-specific shape)

Symphony, slash-commands, and hooks have a **single** orchestration: walk the candidate, run decision points, emit bundle. CC AFK has **two**, because the surface is a duration rather than an instant:

1. **Pre-AFK (`run`)** — the operator commits an `afk-plan.md`, runs `leash-for-cc-afk run <plan>`. Orchestrate validates the plan against decision points and emits a bundle stub: `outputs/run-<hash>/{manifest.json, plan.md, scope-fingerprint.json}`. The bundle is **incomplete** at this point — there is no transcript yet. The bundle's `claim` is `pending_session`.
2. **Post-AFK (`grade`)** — the operator returns, runs `leash-for-cc-afk grade <run-hash> <session-id>`. Orchestrate copies the session transcript into the bundle, runs `cc_session_transcript` over it, fits `scope_violation` against the plan, and writes `transcript.jsonl`, `violations.json`, `grade.json`. The bundle's `claim` flips to `graded` (or stays `pending_session` if the session is not yet ended).

This two-phase shape is **not** a new pattern — it is the same shape as the existing `run` / `verify` split in every leash, just with the verifier running over runtime evidence rather than the candidate-only structure. The `verify.py` for this skill walks both the structural bundle and (when present) the graded session, the same way it walks emitted bundles for sibling leashes.

## Vocal-mode capture path (concrete)

CC writes session transcripts to:

```
~/.claude/projects/<workspace-hash>/<session-id>.jsonl
```

The `<workspace-hash>` is a deterministic hash of the workspace path; for this repo it is `c--Users-bdf19-Desktop-zero-four-experiment` (the same path encoded in the memory directory). The `<session-id>` is the CC-assigned session UUID, visible to the operator at session start.

`collectors/cc_session_transcript.py` (the new AFK-specific collector) walks one such file:

- **Inputs:** `(workspace_hash, session_id)` — an exact path identifier, not a glob.
- **Walk:** parses the JSONL line by line, normalizes each line to a `cc_session_event` data point (turn index, role, content kind, tool calls, file paths touched, source-state at turn).
- **Provenance:** every emitted data point carries `(session_id, turn_index, line_offset)` plus a sha256 of the raw line. The pointer is computed from the live transcript, never authored.
- **Capture in bundle:** post-AFK, the transcript is *copied* into `outputs/run-<hash>/transcript.jsonl` and the copy's sha256 is checked against the live file at grade time. If they diverge (CC wrote more turns after grading), the bundle records `transcript_drift_detected: true` and refuses to claim `graded` until re-graded.

No new infrastructure. CC's transcript writer is already running; the leash just walks its output.

## What's missing to become a Foundation-2 proposal — and the second-override smell

Per [CLAUDE.md](../../CLAUDE.md): *"0.4 emits 4.0 only when 2.0 signals fire."* The recursion-seam extends this: a sibling leash gets built when a signal indicates it should, not when it is requested.

The relevant signal here is **outcome 5** in [recursion-seam.md](../../skills/leash_for_hooks/recursion-seam.md): repeated hand-walking of chain discipline against a surface no existing leash covers.

Status as of this writing (2026-04-30):

- The operator has named CC AFK as a target surface **once**, in this session.
- No prior session in `meeting-notes/` records a CC-AFK hand-walk.
- `proposals/REVIEW.md` does not yet reference CC AFK.
- No `gap_audit` collector for "ad-hoc CC-AFK chain discipline" exists.
- **And: this would be the second override of recursion-seam outcome 5 in a single day.** The first override, [proposals/prop_2026-04-30_leash-for-symphony/override_record.md](../prop_2026-04-30_leash-for-symphony/override_record.md), was logged earlier today for Symphony and explicitly notes that the override authorizes *existence, not promotion*, and is "logged loudly so the next operator (or a future audit) can see exactly what was done and why." Doing it again the same day routinizes what was meant to be loud and exceptional.

The first override had a defensible structural argument: Symphony is a *novel external surface* the operator has just decided to touch, so the seam-gate's "accumulated hand-walks" logic could not apply by construction. **The CC AFK case is weaker on that axis.** CC AFK is not a novel external surface — it is a CC runtime mode, and the operator's prior hand-walking of "what scope is appropriate when going AFK" *can* accumulate. There is no auto-mode-the-feature reason it has to be formalized before it is touched.

Translating: the override argument that worked for Symphony does **not** transfer to CC AFK. Building this leash's skill bundle today, by override, would be doing the override *because the prior override is fresh in mind*, not because the gate is wrong-shaped for this case.

## Two paths for the operator

**Path A — record the directive, build the signal first (seam-conformant, recommended):**

1. Land this README as the design preview (this commit).
2. Build the `surface_handwalk_recurrence` gap collector (the same prereq Symphony's Path A names; this is now blocking *two* leashes' Foundation-2 promotions).
3. The collector retroactively counts this session as occurrence #1 against `surface=cc_afk`. Future AFK sessions accumulate when the operator hand-grades them.
4. When the threshold is crossed, build `skills/leash_for_cc_afk/` as the candidate bundle.

This path is **the conservative move and the seam's default.** It also pays down debt that Symphony's override left outstanding: the gap collector is now load-bearing for two leashes' promotion paths, which makes building it more cost-effective than it was a week ago.

**Path B — operator overrides the seam-gate by fiat again (override-conformant, but vocal):**

1. Land this README plus a companion `override_record.md` that explicitly addresses the second-override-in-one-day concern, and either (a) makes a structural argument distinct from Symphony's, or (b) honestly logs that the override is being granted on momentum and the operator is electing to take that on.
2. Build `skills/leash_for_cc_afk/` immediately as a v0 skill bundle, claim `"candidate"` (no exemplars, fresh corpus).
3. The override_record itself is a 4.0 grading event.

**Recommendation: Path A.** The structural argument that justified Symphony's override does not extend here, and the gap collector is becoming a dependency for multiple leashes — building it next is now more useful than building any individual sibling leash.

## Production placement (post-promotion, either path)

```
skills/leash_for_cc_afk/
├── SKILL.md                            # surface: cc-afk-runtime · rides under: Claude Code
├── leash_state.json                    # {"state": "off", "vocal": true}
├── recursion-seam.md                   # near-verbatim, with runtime-mode notes
├── lib/                                # shared (or imported from bedrock/)
├── collectors/
│   ├── afk_plan_decl.py
│   ├── afk_plan.py
│   ├── cc_session_transcript.py        # new seam, AFK-specific
│   ├── exemplar_bundle_state.py
│   └── llm_sdk_denylist.py             # shared
├── resolvers/                          # shared
├── signals/
│   ├── afk_scope_drift.py
│   ├── scope_violation.py              # new seam, AFK-specific (post-hoc grader)
│   └── emission_readiness.py           # shared
├── orchestrate.py                      # honors state + vocal; two-phase: run + grade
├── verify.py                           # 4.0 grading walker
├── references/
│   └── afk-plan-fields.txt             # taxonomy snapshot
└── outputs/                            # bundles, one per AFK session
```

## Open questions (deferred to candidate phase)

- **Where does `.claude/afk-plans/` live?** A new `.claude/` subdirectory specific to this skill (operator-local), or a tracked `proposals/<...>/candidate/` location (shared). For Symphony the candidate WORKFLOW.md sits under `proposals/`; for CC AFK, since the plan is a per-session contract, `.claude/afk-plans/` (gitignored or selectively committed by operator) is more natural. *Defer.*
- **Does the gap collector need to walk transcripts directly, or only meeting notes + proposals?** Symphony's Path A names "session history, meeting notes, and proposals." For CC AFK, "session history" is the transcript itself — which CC writes per session. The gap collector might want to walk transcripts for "operator hand-graded scope of an AFK session" patterns. *Defer to Path A's scoping.*
- **What is the right `MIN_EXEMPLARS` for the AFK plan corpus?** Operators may produce more AFK plans than WORKFLOW.md files but fewer than hook configurations. Probably tuned lower than 50. *Defer to candidate phase.*
- **Who decides `scope_violation` is a hard fail vs. a flag?** A violation could mean (a) the agent went rogue, or (b) the operator's plan was under-scoped and the necessary work was outside it. The signal emits the verdict; the operator decides the action. The skill should not auto-rollback. *Resolved here:* the leash never executes mitigation — it grades and reports.

## What this preview does not authorize

- It does **not** create `skills/leash_for_cc_afk/`.
- It does **not** create `override_record.md` for this surface.
- It does **not** touch any existing `leash_state.json`.
- It does **not** lift `vocal` into the shared validator (even though this is the second leash to use it; that lift is its own micro-proposal).

The next concrete move, if Path A is chosen, is to build the `surface_handwalk_recurrence` gap collector — a single 1.0 collector (under 0.1 protocol) under [skills/gap_audit/](../../skills/gap_audit/) that walks the operator's session corpus for repeated ad-hoc chain-discipline application against a named surface. That collector becomes the prereq for Foundation-2 promotion of both this proposal and the Symphony proposal.
