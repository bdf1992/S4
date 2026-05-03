# Heartbeat pattern — design preview

**Status:** design preview, **not** a Foundation-2-verified proposal yet. See "What's missing" below. This document is a 0.1 spec draft for a parameterized ritual-dispatch pattern that hooks heartbeat-able skills into a configurable schedule with subagent fan-out and loop primitives. It does not ship a runner, a contract validator, or a config schema validator — only the spec those would attach to. Authored by a 3.0 routine in response to operator framing turns on 2026-05-03 (transcript pointer at end).

This file uses the two-axis programs-vs-protocols framing from [CLAUDE.md](../../CLAUDE.md): X.0 names program kinds (1.0 handwritten, 2.0 learned, 3.0 prompted, 4.0 coupled); 0.X names the protocols that produce them; 0.0 is the candidate state.

---

## What this pattern is

A **heartbeat** is a 1.0 dispatch program that reads a config of (ritual → cadence → gate → dispatch surface), ticks on schedule, queries each ritual's gate signal, and on fire launches a subagent that runs the ritual. It is the floor that makes any operator-defined ritual (scrum, books-close, gap-audit, verify-walk) survive a 19:1 no-commit-cook ratio without re-engineering per ritual.

The heartbeat is **dispatch, not orchestration logic.** It does not decide *what* a ritual does — that lives in the ritual's own skill. It decides *whether* to fire (gate query), *how many parallel forks* (fan-out over a step's structured output), and *what to thread through* (parameter substitution from prior steps). A heartbeat that contains ritual-specific logic is a 3.0 free-write claiming to be dispatch.

The heartbeat is **composable, not monolithic.** A config is a sequence of `[[step]]` entries; each step names a ritual skill, a gate, optional `fan_out` over a prior step's output, and optional `args` interpolating prior outputs. `loop = true` makes the tail step re-enter the head. Same primitive shape covers `scrum → 10 cooks` and `gap_audit → fan-out fix sessions per gap` and `verify-walk → fan-out decision drafts per new pass`.

## The ritual contract (what makes a skill heartbeat-able)

A skill becomes hookable by declaring a **`heartbeat.json`** sibling to `SKILL.md` with exactly these fields:

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `ritual_id` | string | yes | Stable handle. Format: `ritual:{slug}`. Slug is `[a-z0-9_]+`. Example: `ritual:scrum`. |
| `gate_pointer` | pointer ([Foundation 3](../../foundations/pointer.md)) | yes | `kind=symbol`. Resolves to a deterministic function `should_fire(state) → bool`. Pure: reads source, no LLM, no clock-of-its-own. Example: walks git log + last receipt to return `commits-since-last-fire > 0`. |
| `idempotency_key_pointer` | pointer | yes | `kind=symbol`. Resolves to `idempotency_key(state) → str`. Two ticks on the same key are coalesced — only the first fires; later ticks return the cached receipt. Closes double-fire. |
| `output_schema_pointer` | pointer | yes | `kind=symbol`. Resolves to a JSON Schema describing the ritual's structured output (the `output.json` sidecar — see below). The contract that downstream `fan_out` and `args` substitution attaches to. |
| `receipt_dir` | path | yes | Where fire-events land. Format: `<skill>/heartbeat_receipts/`. Each receipt is `{ritual_id, fired_at, source_state, idempotency_key, output_path, dispatch_surface, exit_code}`. |
| `output_writer_pointer` | pointer | yes | `kind=symbol`. Resolves to `write_output(receipt_dir, structured) → path`. Writes the `output.json` sidecar matching `output_schema_pointer`. The single seam where the ritual's prose-vs-structured boundary lives. |
| `dispatch_surfaces_supported` | list[enum] | yes | Subset of `["agent-subagent", "scheduled-remote", "loop"]`. Declares which dispatch surfaces this ritual is safe under. A ritual that mutates working-tree state may not declare `scheduled-remote`. |
| `audit_budget_lines` | integer | yes | Maximum substantive line count for `gate_pointer` and `output_writer_pointer` source files combined. Same audit-budget discipline as collectors ([Foundation 2](../../foundations/collection-program.md)). |

A skill without `heartbeat.json` is not hookable. A skill with a malformed `heartbeat.json` is rejected by the heartbeat runner's `verify.py` — it does not silently get scheduled.

## The heartbeat config shape

A heartbeat config lives at `heartbeats/<name>.toml`. Each file is one heartbeat. Operator-authored, version-controlled, reviewable.

```toml
# heartbeats/scrum_and_cooks.toml — example

schedule = "daily@08:00"          # cron expression OR "every Nm/h" OR "on-event:<signal_id>"
surface  = "scheduled-remote"      # one of the ritual's declared dispatch_surfaces_supported, applied to all steps
loop     = true                    # if true, tail step re-enters head step on completion

[[step]]
id    = "scrum"
skill = "scrum"
gate  = "commits-since-last-fire(self) > 0"   # gate-expression DSL; queries gate_pointer + state

[[step]]
id      = "cook_targets"
skill   = "cook"
depends = ["scrum"]                            # explicit DAG edge; required if step references prior step
fan_out = "{{ steps.scrum.next_targets[:10] }}"  # spawns N subagents, one per element; element bound to {{ item }}
args    = { target = "{{ item.skill }}", mode = "solve" }
```

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `schedule` | string | yes | Cron expression, interval shorthand (`every 4h`), or event hook (`on-event:<signal_id>`). The scheduler resolves to a tick stream. |
| `surface` | enum | yes | Dispatch surface for all steps. Subset must intersect every referenced ritual's `dispatch_surfaces_supported`. |
| `loop` | bool | no (default false) | If true, after tail step's receipt lands, runner re-enters head step. Loop guard: max-iterations field below. |
| `max_iterations_per_tick` | integer | no (default 1) | Cap for `loop = true` to prevent runaway. Operator-set. |
| `[[step]]` | array | yes (≥1) | Sequence of step records (see below). |

**Step record fields:**

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | string | yes | Step handle for downstream reference. Unique within file. |
| `skill` | string | yes | Ritual skill name. Must have valid `heartbeat.json`. |
| `gate` | gate-expression | no (default: ritual's own gate) | Override the ritual's default gate. Limited DSL: comparisons over `commits-since-last-fire(self)`, `last-receipt-age`, `signal:<id>`. |
| `depends` | list[step.id] | no | Explicit DAG edges. Required if `fan_out` or `args` references a prior step. |
| `fan_out` | jq-style template | no | Resolves to a list at runtime; spawns one subagent per element. Element bound to `{{ item }}` in `args`. |
| `args` | dict | no | Argument map passed to the ritual skill. Values may interpolate `{{ steps.<id>.<field> }}` or `{{ item.<field> }}`. |
| `surface_override` | enum | no | Per-step surface override. Must be in the ritual's `dispatch_surfaces_supported`. |

**Substitution rule:** `{{ steps.<id>.<field> }}` resolves against the prior step's `output.json` (the structured sidecar written via `output_writer_pointer`). Substitution against a step's prose receipt is rejected — only structured output is referenceable. This forces rituals to expose what they want composed-on, deliberately, via their `output_schema_pointer`.

## The heartbeat runner sketch

The runner is itself a 1.0 program (one source file, deterministic dispatch logic, no LLM in the dispatch path — the LLM lives only in the *subagents it launches*). Sketch:

```
runner.tick(config_path, now) -> list[receipt]

  config = load_and_validate(config_path)         # rejects if any step.skill lacks valid heartbeat.json
  if not schedule_matches(config.schedule, now):
      return []

  receipts = []
  iterations = 0

  while iterations < config.max_iterations_per_tick:
      step_outputs = {}
      for step in config.steps:
          ritual = load_ritual(step.skill)         # reads heartbeat.json
          state  = current_source_state()

          if not gate_evaluates_true(step.gate or ritual.default_gate, state):
              record_skip(step, state, reason="gate_false")
              continue

          idempotency_key = ritual.idempotency_key(state)
          if receipt_exists_for(ritual, idempotency_key):
              step_outputs[step.id] = load_cached_output(ritual, idempotency_key)
              continue

          if step.fan_out:
              items   = resolve_template(step.fan_out, step_outputs)
              subagents = [
                  dispatch(config.surface, ritual, render_args(step.args, step_outputs, item))
                  for item in items
              ]
              outputs = await_all(subagents)
              step_outputs[step.id] = aggregate(outputs)
          else:
              args   = render_args(step.args, step_outputs)
              output = dispatch(config.surface, ritual, args)
              step_outputs[step.id] = output

          receipts.append(record_fire(step, state, idempotency_key, output))

      if not config.loop:
          break
      iterations += 1

  return receipts
```

The dispatch function is the only place the runner touches a Claude Code surface. Three implementations, one per surface enum:

- `dispatch("agent-subagent", ...)` — calls Claude Code's `Agent` tool with `subagent_type="general-purpose"` (or a ritual-declared subagent type), prompt = ritual's invocation template + rendered args. Runs in operator's active session.
- `dispatch("scheduled-remote", ...)` — emits a `schedule` payload (one-shot) for the ritual; remote agent picks it up. Runs while operator is asleep.
- `dispatch("loop", ...)` — emits a `ScheduleWakeup` continuation in the operator's active session. Used when the ritual itself wants to self-pace.

Each dispatch returns when the subagent's receipt lands (sync within tick) or returns a future (async; tick yields after fan_out spawn, resumes when all join).

## Examples across the 0.0–0.4 ladder

The same primitive shape covers heartbeats at every layer of the chain:

**0.0 candidate emission loop** (`heartbeats/propose_skills.toml`):

```toml
schedule = "every 6h"
surface  = "agent-subagent"
loop     = false

[[step]]
id    = "scan_floor"
skill = "floor_growth"
# emits structured: { isolated_with_signals: [...], no_structure: [...] }

[[step]]
id      = "draft_proposals"
skill   = "propose"
depends = ["scan_floor"]
fan_out = "{{ steps.scan_floor.no_structure[:5] }}"
args    = { kind = "skill_without_verifier", target = "{{ item }}" }
```

**0.1 floor-walk** (`heartbeats/floor_check.toml`): scan floor → if any verify.py regression, fan-out cooks to repair. Same step shape; `fan_out` reads regression list.

**0.2 signal sweep** (`heartbeats/signal_sweep.toml`): walk every `signals/*.py`, run each, fan-out 3.0 fix sessions per fired signal. The runner does not understand "signal" — it just dispatches what the gate emits.

**0.3 graduation walk** (`heartbeats/graduation_walk.toml`): walk every `verify.py` → for each newly-passing skill not yet decided in `decisions.jsonl`, fan-out a `propose-decision` subagent. Closes the rung-4 (peer use) gap by surfacing graduated candidates for operator decision.

**0.4 bundle pointer-freshness** (`heartbeats/bundle_check.toml`): walk every bundle → for each dangling pointer, fan-out a repair session. The 4.0 grading procedure from [foundations/zero-four.md](../../foundations/zero-four.md) becomes a heartbeat-driven loop, not a one-shot ritual.

In every case, the heartbeat config is small, declarative, and operator-authored. The dispatch logic is shared.

## Dispatch surface tradeoff

| Surface | Pros | Cons | Use when |
| --- | --- | --- | --- |
| `agent-subagent` | Fast, no remote-agent cost, operator sees results inline | Only ticks while operator is in Claude Code; lost if session ends mid-tick | Ritual is fast (<2min), operator wants results in current session, fan-out count low (<10) |
| `scheduled-remote` | Runs while operator is asleep; survives session end; truly autonomous | Each tick is fresh context; per-tick cost; results land async | Daily/hourly cadence, ritual is self-contained, fan-out count high or unknown |
| `loop` | Maintains continuity within a session; cheap (no new context) | Ties up operator's session; only one running at a time | Active monitoring (cook-grounding, trace-health), interactive iteration |

The pattern supports all three so a ritual can declare which surfaces it's safe on, and the operator picks per-config.

## Retrofit candidates

Skills already shaped to declare `heartbeat.json` cleanly (read source → emit markdown → exit, idempotent on source_state):

- `scrum` — gate: `commits-since-last-fire > 0 OR open-proposals-changed OR decisions.jsonl appended`. Output: `next_targets`, `open_threads`, `floor_ratio`. Composable with `cook` fan-out (the example above).
- `standup` — gate: `daily, on-tick`. Output: same shape as scrum, narrower window.
- `books-close` — gate: `monthly@end-of-month`. Output: `decisions_landed`, `proposals_pending`. Composable with `propose-decision` fan-out.
- `render_proposals` — gate: `proposals/ changed`. Output: list of newly-rendered proposals. Composable with notification surfaces.

Skills that are NOT good fits (do not declare `heartbeat.json`):

- `cook-grounding`, `trace-health` — reactive, want to *watch* a stream, not *tick*. Different pattern (event subscriber, not heartbeat dispatcher). Don't fuse.
- Any skill that mutates source as a side-effect (e.g. `verify.py` that writes datasets) — these are collectors, not rituals; they get *called by* hookable skills, not hooked themselves.

## Detectable violations

Each violation MUST be detectable by a 0.1 program (the runner's `verify.py`). A violation requiring human or model judgement indicates a hole in this spec.

| Violation | How it is detected |
| --- | --- |
| Required field missing or extra field present in a `heartbeat.json` | Schema validator on `heartbeat.json`. |
| `ritual_id` does not match `ritual:{slug}` format | Format validator. |
| `gate_pointer`, `output_writer_pointer`, or `idempotency_key_pointer` dangles | Pointer re-resolution at run-time. |
| Function under `gate_pointer` imports an LLM SDK or uses banned nondeterminism | Foundation-2 static check on the source file. |
| `output_schema_pointer` resolves to invalid JSON Schema | Schema validator. |
| Heartbeat config references a `step.skill` that lacks `heartbeat.json` | Cross-check on config load. |
| Heartbeat config's `surface` is not in a referenced ritual's `dispatch_surfaces_supported` | Cross-check on config load. |
| Step references `{{ steps.<id>.<field> }}` for a step not in `depends` | DAG validator. |
| Step references `{{ steps.<id>.<field> }}` for a field not in that step's `output_schema_pointer` schema | Schema cross-check. |
| `loop = true` without `max_iterations_per_tick` set | Schema validator. |
| `audit_budget_lines` exceeded by gate or output_writer source files | Static line count. |
| Receipt for fire-event missing `source_state` or `idempotency_key` | Receipt schema validator. |
| Two fires on the same `idempotency_key` produce different `output.json` (cache divergence) | Receipt-corpus consistency check. |
| `gate_pointer` returns non-bool | Type check on first invocation. |

A heartbeat config or `heartbeat.json` failing any check is rejected. The runner does not tick under invalid config.

## What this pattern is not

- **Not a workflow engine.** No conditional branching beyond gate-skip, no nested DAGs, no joins beyond `fan_out` aggregate. The shape is intentionally narrow — wide enough for ritual chains, narrow enough to stay 1.0-shaped. If a use case requires Airflow shape, write a 3.0 orchestration skill, not a heartbeat config.
- **Not a generator.** The heartbeat does not invent rituals or steps based on natural-language intent. Every step is a hand-authored config entry pointing at a hand-authored ritual.
- **Not a 2.0 signal.** The heartbeat fires when its gate (a 1.0 collector) returns true. The gate may *consult* a 2.0 signal (`gate = "signal:cook_no_commit_rate > 0.5"`) but the heartbeat itself is dispatch logic, not learned policy.
- **Not a quality gate.** A heartbeat tick produces work; the work's correctness is judged by the rituals' own contracts and the 4.0 bundle-walk discipline. The heartbeat does not gate merges or block commits.
- **Not bedrock.** This contract is derived. It can be revised when experience shows it should be — every revision bumps a `pattern_version` field stamped on every receipt. The four foundations remain the immovable layer.

## Why this shape

Each constraint exists to close a specific failure mode:

- **Ritual contract as separate `heartbeat.json`** closes *implicit hookability*. A skill that "happens to be runnable on a timer" because someone wrote a cron entry is not the same as a skill that *declared* it is hookable. The contract makes the property auditable.
- **Structured `output.json` sidecar required for composition** closes *prose-as-data substitution*. If `{{ steps.scrum.next_targets }}` parses scrum's markdown, the substitution is brittle and the chain breaks every time the markdown shape drifts. Forcing rituals to publish structured output via a declared schema makes composition contract-bound.
- **Idempotency key required and cached** closes *double-fire*. Without it, a heartbeat that fires twice on the same source state runs the ritual twice, producing two no-commit cooks (the exact leak this pattern is meant to fix).
- **Dispatch-surface declared per ritual** closes *wrong-surface dispatch*. A ritual that mutates working-tree state cannot safely run in a fresh-context scheduled remote (no working tree to mutate). The contract refuses that combination at config-load time.
- **Audit budget on `gate_pointer`** closes *quiet gate drift*. A long gate function can silently incorporate new conditions; a small one cannot hide them. Operator can review every gate at a glance.
- **No conditional branching beyond gate-skip** closes *workflow-engine creep*. The first time someone wants `if/else`, the right answer is a new ritual that encapsulates the decision, not a heartbeat config that grows another DSL feature. Holding the shape narrow keeps the runner a 1.0 program forever.
- **`{{ item }}` binding for fan-out, no nested fan-out** closes *combinatorial explosion*. Fan-out of fan-out is a 3.0 task; if the operator wants `for-each-of-each`, they author a skill that does the inner loop and configure single-level fan-out at the heartbeat layer.

Holding all of these at once is what lets the heartbeat be a small, durable 1.0 dispatch program that never absorbs ritual-specific logic — and what lets the floor of hookable rituals grow without the runner growing.

## What's missing to become a Foundation-2-verified proposal

Per [CLAUDE.md](../../CLAUDE.md), "0.4 emits 4.0 only when 2.0 signals fire." The measured gap this proposal attaches to is the **19:1 no-commit-cook ratio** surfaced in the 2026-05-03 scrum (19 cook events with no commit landed, 1 cook event with commit). That ratio IS a measured gap — it indicates that ritual invocations are not landing receipts at the rate the cook discipline assumes — but the gap collector that measures it is currently part of the standup composer, not a free-standing 1.0 collector.

To upgrade from design preview to proposal:

1. **Extract the no-commit-cook ratio collector** out of [tools/standup.py](../../tools/standup.py) into a free-standing 1.0 collector under [skills/gap_audit/collectors/](../../skills/gap_audit/collectors/). It walks cook receipts and commit history, emits a `cook_no_commit_rate` data point per window. Today's reading is the gap evidence that motivates the heartbeat pattern.

2. **Build the heartbeat runner spec's `verify.py` outline** (separate doc `prop_2026-05-XX_heartbeat-runner-verify/`). It walks `heartbeats/` + every referenced ritual's `heartbeat.json` and exits non-zero on any violation in the table above. The runner is not the verifier — the verifier is its own 1.0 audit program.

3. **Pick one retrofit candidate (recommend `scrum`) and write its `heartbeat.json` end-to-end** — including the structured `output.json` sidecar emitted by [tools/standup.py](../../tools/standup.py). This proves the contract holds against a real ritual before the runner is built, and provides the first reference implementation.

4. **Build one heartbeat config end-to-end** — the `scrum_and_cooks.toml` example above — and dispatch it once manually through the operator's session (no runner yet) to validate the substitution and fan-out shapes hold. This is the smoke test the runner spec attaches to.

Until step 1, this is a 0.0-stage design exercise authored by a 3.0 — useful for evaluation, **not yet a graduated 0.1 floor**.

## Operator transcript pointer

Operator framing turns that authorize this draft, in chronological order on 2026-05-03:

- "I want to be able to hook our ritual into a heartbeat, so they run on a schedule/loop, throughts?" — established the pattern's purpose: rituals (scrum, books-close, etc.) need a recurring fire surface, not just on-demand invocation. Framed against the measured 19:1 no-commit-cook ratio surfaced in the same scrum.
- "I want to fix the problem forever, and creating skills, which loop, based on a configuration of a heartbeat, launching subagents would be amazing to land as a pattern" — established the ambition: not a one-off heartbeat for one ritual, but a *pattern* (config + contract + runner) that any ritual can hook into without re-engineering. Established subagent dispatch as the launch mechanism.
- "As long as I can pass argument with a skill like configure the hearbeat skill to run the scrum and 10 cook sessions based on the scrum targets and loop it. Or other such concepts related to 0.0-4.4 +" — established conditional approval with a load-bearing constraint: parameter-passing between steps, fan-out over a step's structured output, and loop-back must be first-class. Established that example workflows should span the 0.0–0.4 protocol ladder, not just standup-style rituals.

Per the operator-intent-via-transcript-pointer discipline, the verbal directives in the session transcript are the authorization for this draft. The transcript file lives at `~/.claude/projects/{project_path}/{session}.jsonl`; the three turns above appear in sequence on 2026-05-03.
