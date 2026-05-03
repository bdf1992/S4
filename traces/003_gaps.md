# Hand-play 003 — gaps surfaced

**Trace:** [`runner_trace.jsonl`](runner_trace.jsonl) line 3 (`trace:003`)
**Config:** [`heartbeats/scrum_fanout_cook.toml`](../heartbeats/scrum_fanout_cook.toml) — scrum + fan_out cook over `next_targets[0].skills`. Tests: `[N].field` substitution, fan_out, per-item idempotency.
**Runner:** [`traces/handplay_003_runner.py`](handplay_003_runner.py) — first version of the runner that's not just a markdown trace; this script IS the proto-runner.
**Substitution test:** `{{ steps.scrum.next_targets[0].skills }}` → `["leash_for_slash_commands", "leash_for_symphony"]`. Each item rendered into per-cook `args`. Verified.

**Decision-step ratio:** **22 deterministic / 24 total**. Both judgment calls are the same gap (GAP-18: real Agent-tool subagent dispatch) manifesting once per fan_out item. The runner script ran end-to-end without my needing to make a single judgment call at runtime — the proto-runner is **88% authored, 12% gap-marker**.

---

## Gaps closed since hand-play 002

| Gap | Closure |
| --- | --- |
| GAP-14 (gate/idempotency hard-coded scrum dir) | [`tools/standup.py`](../tools/standup.py): `heartbeat_gate(receipt_dir, state)` and `heartbeat_idempotency_key(receipt_dir, state)` — ritual-agnostic |
| GAP-15 (substitution parser unspecified) | [`tools/heartbeat_template.py`](../tools/heartbeat_template.py): supports dotted access, `[N]` index, `[:N]` slice, `item` binding, embedded substitution in larger strings |

## NEW gaps surfaced in hand-play 003

### GAP-20 — Chain semantics on idempotent-skip require receipt → sidecar pointer

When a step's gate returns False (idempotency hit), the runner must use the cached output from the prior receipt to satisfy downstream substitution. Hand-play 003 did this by reading `last_receipt["sidecar_path"]`, loading the sidecar JSON, and binding it to `step_outputs[step_id]`.

This works only because the receipt format already includes a `sidecar_path` field — but the proposal hasn't required it. **Receipt schema must mandate `sidecar_path` as a required field**, and the runner spec must say "on gate=False, load `_last_receipt[receipt_dir]['sidecar_path']` into `step_outputs[step_id]`."

This is a small fix (one schema field + one paragraph in the proposal), but it's the load-bearing rule that makes idempotency play with chains. Without it, every chain re-fire either needs to re-dispatch every step or breaks downstream.

### GAP-21 — Aggregation shape needs a downstream-substitution rule

After fan_out, `step_outputs[step_id]` becomes `list[dict]` (one per item). A downstream step that wants to reference the *aggregate* needs syntax like:

- `{{ steps.cook_targets[0].session_id }}` — works today, single item access.
- `{{ steps.cook_targets.session_id }}` — DOESN'T work; would need automatic field-pluck (`[item.field for item in list]`).
- `{{ steps.cook_targets[*].session_id }}` — wildcard, deliberately not supported per `heartbeat_template` doc.

Hand-play 003 doesn't have a downstream step depending on `cook_targets`, so this didn't fail today. But the proposal example `scrum → cooks×10 → notify-on-failure` would hit it.

**Resolution paths:**
- (a) Keep template narrow; require a `[N]` index on aggregated results. Forces operator to think one-at-a-time.
- (b) Add a deliberate field-pluck rule: `{{ steps.X.field }}` where X is a list → `[item.field for item in X]`. Cheap, consistent.
- (c) Add an aggregator step type that turns `list[dict]` into `dict[list]` explicitly. Most flexible, most config noise.

(b) is the right default. Surfaces no surprise for single-item access (still works) and one-paragraph rule for the aggregate case.

### GAP-22 — Contract needs `required_args` declaration (resolved inline)

scrum and standup take no required args. Cook *needs* `target` to do meaningful work. The runner must validate args before dispatch. Added `required_args: ["target"]` to [`.claude/skills/cook/heartbeat.json`](../.claude/skills/cook/heartbeat.json); proto-runner enforces. Should be lifted into the proposal's contract spec.

## Gaps still open from hand-plays 001-002

| Gap | Status | Path forward |
| --- | --- | --- |
| GAP-1 | open: contract location ambiguity | Proposal spec change: "walk `**/heartbeat.json`" |
| GAP-2/3 | open: Foundation 3 doesn't define symbol-pointer target format; no symbol_resolver | Larger spec change to Foundation 3 (4.0 grading event) — defer until clearly load-bearing |
| GAP-12 | partial: trace records all 3 source_states | Pick one as primary in proposal |
| GAP-16 | open: step_outputs persistence per surface | Proposal addition: "substitution resolves runner-side, dispatched ritual receives concrete args only" |
| GAP-17 | resolved-by-construction | Per-step idempotency composes to chain-level; no separate key |
| GAP-18 | **largest open gap**: real Agent-tool subagent dispatch | Wants its own proposal: `prop:2026-05-XX:agent-subagent-dispatch-shape` |
| GAP-19 | resolved-in-proto-runner | Filename = `<session_id>.{json,receipt.json}`. Stable. |

---

## What this hand-play validated

- **Fan_out mechanically works.** `[[step]] fan_out = "{{ ... }}"` resolved to a real list, looped over with per-item args rendering and per-item gate/idempotency.
- **Per-item idempotency is the right shape.** `cook_idempotency_key` includes target, so two ticks at the same HEAD with same fan_out items collapse correctly while different items remain independent.
- **Cached output on gate=False.** scrum's gate returned False (HEAD unchanged since 002 receipt); proto-runner loaded the prior sidecar and chain continued. The idempotency-and-cache pattern is implementable and the cost is one extra schema field on receipts.
- **88% deterministic ratio at 24 steps.** Up from 17/21 in 002 and 3/10 in 001. The methodology is converging — each hand-play surfaces fewer gaps because each prior closure removed a class of judgment calls. **This is what shadow-design predicted: the 1.0 runner becomes writeable as the trace stabilizes.**

## What this hand-play did NOT exercise

- Downstream-of-fan_out substitution (would surface GAP-21 in practice).
- Real concurrency (proto-runner dispatched fan_out items sequentially, not parallel). Concurrency is GAP-18-adjacent — real subagent dispatch IS what enables parallelism.
- Loop re-entry (`loop = true`).
- `scheduled-remote` surface.
- A second-tick re-fire to validate caching against a fresh tick (caching was implicit via the prior 002 receipt).

## What is now writeable as 1.0

The proto-runner script [`traces/handplay_003_runner.py`](handplay_003_runner.py) is **88% the spec for `tools/heartbeat_runner.py`**. The rule of thumb from the methodology — "crystallize when traces stabilize across 5–10 hand-plays" — is met early on most rungs:

| Runner concern | Status | Lines of judgment-marker code |
| --- | --- | --- |
| config discovery + parsing | stable | 0 |
| schedule check (operator-triggered only) | stable | 0 — needs cron/event hookup for real |
| ritual-contract loading | stable | 0 |
| gate evaluation | stable | 0 |
| cached-output loading on skip | stable | 0 (needs receipt schema field) |
| substitution rendering | stable | 0 |
| fan_out dispatch loop | stable | 0 |
| **per-item dispatch (Agent-tool surface)** | **GAP-18** | the only judgment-marker call |
| receipt writing | stable | 0 |
| aggregation | stable | 0 |

The next hand-play (004) does not need to be a fan_out exercise; it should be **`loop = true`** (re-entry semantics) AND/OR a downstream-of-fan_out substitution test (forces GAP-21 closure path). Or, alternatively, the work shifts into closing GAP-18 for real (writing `tools/heartbeat_runner.py` with an `Agent`-tool-using dispatch surface), since that's the largest remaining pivot.

## Suggested next move

Two directions, operator's choice:

**(A) Hand-play 004:** test `loop = true` + downstream-of-fan_out substitution. Cheaper. Surfaces GAP-21 closure shape. Continues shadow-design.

**(B) Crystallize: write `tools/heartbeat_runner.py`.** Take `traces/handplay_003_runner.py` as the spec, lift 22/24 stable steps into a real runner module, leave GAP-18 (subagent dispatch) as a clearly-marked TODO with an interface stub. Let real heartbeats fire against scrum/standup/cook without further hand-play. This crosses from shadow-design into actual implementation.

**(C) Crystallize the receipts schema + verify.py.** Write `schemas/heartbeat_receipt.json` (with mandatory `sidecar_path` per GAP-20 fix), and write `tools/verify_heartbeats.py` (the runner's verify.py from the proposal — walks `heartbeats/`, every `heartbeat.json`, validates the contract table from the proposal). This is the proposal's "graduate to Foundation-2-verified" step.

Stopping shadow-design here for operator decision on direction.
