# Hand-play 002 — gaps surfaced

**Trace:** [`runner_trace.jsonl`](runner_trace.jsonl) line 2 (`trace:002`)
**Config:** [`heartbeats/scrum_then_standup.toml`](../heartbeats/scrum_then_standup.toml) — two-step chain, `depends`, parameter substitution. No fan_out (that's hand-play 003). No loop.
**Substitution test:** `{{ steps.scrum.window.until_iso }}` → `"2026-05-03T06:21:51+00:00"` → standup's `--since`. **Verified end-to-end:** standup's emitted sidecar reports `window.since_iso == 2026-05-03T06:21:51+00:00`. Substitution actually flowed through real source.

**Decision-step ratio:** 17 deterministic / 21 total (vs 3/10 in hand-play 001). The 8 newly-deterministic steps came from closing GAP-7/8 (structured output exists), GAP-4/6 (gate + idempotency functions exist with explicit bootstrap rule), and GAP-10/11 (surface enum + audit budget reshaped). The remaining 4 judgment calls all cluster at substitution and per-ritual binding of shared functions.

---

## Gaps closed since hand-play 001

| Gap | Closure |
| --- | --- |
| GAP-7 (no JSON schema) | [`schemas/scrum_output.json`](../schemas/scrum_output.json) — covers both standup and scrum modes |
| GAP-8 (no output writer) | [`tools/standup.py`](../tools/standup.py) `_collect_structured()` + `--emit-structured PATH` flag |
| GAP-4 (no `should_fire(state) → bool` function) | [`tools/standup.py`](../tools/standup.py) `heartbeat_gate()` |
| GAP-6 (first-tick bootstrap undefined) | Rule chosen: no prior receipt → fire; idempotency key includes "bootstrap" marker |
| GAP-9 (receipt dir collides with .gitignore) | Receipts moved to top-level `heartbeats/receipts/<ritual>/`; gitignore unaffected |
| GAP-10 (`dispatch_surfaces_supported` conflated safe vs wants) | Split into `dispatch_surfaces_safe` + `dispatch_surfaces_recommended` in heartbeat.json |
| GAP-11 (file-level audit budget breaks for shared modules) | Switched to per-symbol budget (AST-walk the named symbol) |
| GAP-13 (receipt vs sidecar collision) | Reorganized: `heartbeats/outputs/<ritual>/` for ritual products, `heartbeats/receipts/<ritual>/` for runner audit records (suffix `.receipt.json` to disambiguate further) |

## Gaps still open from hand-play 001

| Gap | Status |
| --- | --- |
| GAP-1 (contract location: `skills/` vs `.claude/skills/`) | Workable rule chosen ("walk `**/heartbeat.json`") but not formalized in proposal yet |
| GAP-2/3 (Foundation 3 doesn't define symbol-pointer target format; no symbol_resolver) | Still open. Pointers in heartbeat.json files remain placeholders for now; the *named functions* are real and callable from Python, just not via a Foundation-3 resolver |
| GAP-5 (idempotency-key recursive on receipt history) | Closed by the bootstrap rule (GAP-6) — first tick uses "bootstrap" marker, subsequent ticks read last receipt's `fired_at` |
| GAP-12 (config_hash, composite source_state) | Still trace-level placeholder |

## NEW gaps surfaced in hand-play 002

### GAP-14 — Shared gate/idempotency functions are bound to one ritual's receipt_dir

`heartbeat_gate()` and `heartbeat_idempotency_key()` hard-code `heartbeats/receipts/scrum/` as the path they walk. Both standup and scrum point at the same functions in their `heartbeat.json` files. When the runner evaluated standup's gate, it read scrum's receipts, not standup's — accidentally correct here only because no receipts existed at all (bootstrap path).

**Resolution paths:**
- (a) Add `ritual_id: str` parameter to both functions; runner passes the calling ritual's id.
- (b) Have each ritual carry its own gate/idempotency function (no sharing).
- (c) Read `receipt_dir` from the ritual's `heartbeat.json` and pass it as state.

(c) is cleanest — it makes the function ritual-agnostic and the ritual-specific config lives where it belongs (in the contract). Worth doing before hand-play 003.

### GAP-15 — Substitution syntax/parser unspecified

The proposal says `{{ steps.<id>.<field> }}` resolves against prior step structured output. Hand-play 002 resolved one substitution by hand using Python `dict["steps"]["scrum"]["window"]["until_iso"]`. The runner needs a real parser — but which?

**Options:**
- (a) jq syntax — powerful, well-known, but adds external dependency.
- (b) JSONPath-lite — covers `.foo.bar`, `[N]`, `[*]`. Implementable in ~30 lines.
- (c) Plain Python format strings with dotted access — simplest, but no slicing/filtering for `fan_out` selectors like `[:10]`.

The proposal's `scrum → cooks×10` example uses `{{ steps.scrum.next_targets[:10] }}` — slice syntax mandatory for the headline use case. Need at least (b)-shape with slice support.

### GAP-16 — Where do step_outputs live during a tick (per-surface answer differs)

For `agent-subagent` surface, the runner holds `step_outputs` in memory between dispatches. For `scheduled-remote`, each subagent is a fresh context — there is no shared memory. The runner must resolve all substitutions BEFORE dispatch and pass rendered args in the prompt body, not as live references.

**Implication for the contract:** substitution is purely a runner-side concern, never visible to the dispatched ritual. Rituals receive concrete strings/numbers, never `{{ ... }}` templates. Worth declaring explicitly in the proposal.

### GAP-17 — Chain-level idempotency vs per-ritual idempotency

When the chain re-runs at the same git HEAD, each ritual's idempotency_key collapses individually (good — no duplicate fires). But there's no chain-level key. If a chain re-runs after a partial failure (e.g. step 1 fired, step 2 crashed), how does the runner know to skip step 1 and just retry step 2?

**Resolution path:** chain-level idempotency = the composition of per-ritual idempotency. Step 1 was fired this tick iff its receipt for the current key exists; step 2 fires iff its receipt doesn't. This is automatic if the runner just checks per-step receipts before dispatch — no separate chain key needed.

### GAP-18 — Real subagent dispatch (Claude Code Agent tool) interface unspecified

Hand-play 002 used the Bash tool directly to invoke `python -m tools.standup`. Real `agent-subagent` dispatch should use Claude Code's `Agent` tool with a fresh subagent context. The interface the runner needs:

- Prompt template per ritual (where to put rendered args, how to ask the subagent to write its receipt)
- Subagent return signal (how does the subagent confirm "I wrote my receipt at PATH"?)
- Failure modes (subagent OOMs, returns garbage, never returns)

This is a real Claude-Code-specific design problem. Not solvable without an Agent-tool spike. Recommend a separate proposal: `prop:2026-05-XX:agent-subagent-dispatch-shape`.

### GAP-19 — Sidecar/receipt naming convention not deterministic

Hand-play 002 named files `handplay-002-step1.json` by hand. An automated runner needs a naming scheme: `<ritual_id>/<idempotency_key>.{md,json,receipt.json}`? Or `<ritual_id>/<fired_at_iso>.{md,...}`? Or both?

**Resolution path:** filename = `<idempotency_key>.{md,output.json,receipt.json}` (key already encodes git HEAD + last_iso, which uniquely identifies the fire). Iso-timestamped filenames are advisory only.

---

## What this hand-play validated

- **Substitution mechanically works.** A field from one ritual's structured output flows correctly into another ritual's args via real source-walking dispatch. No conceptual blocker.
- **Bootstrap rule is sufficient.** The first-tick "no prior receipt → fire" rule worked through both rituals without special-casing.
- **The output_dir / receipt_dir split is right.** Two distinct concerns, two distinct directories, no further confusion in this hand-play.
- **The audit-budget per-symbol resolution holds.** scrum's named functions (`heartbeat_gate` ≈ 18 lines, `_collect_structured` ≈ 40 lines) total ≈ 58 — under the 60-line budget without contortion.

## What this hand-play did NOT exercise

- `fan_out` over a list (next: hand-play 003)
- `loop = true` re-entry
- `scheduled-remote` dispatch surface (hard — needs the `schedule` skill spike)
- Real Claude Code `Agent`-tool subagent dispatch (GAP-18)
- Multiple parallel substitution resolutions (only one substitution in this hand-play)

## Suggested next move

**Hand-play 003: fan_out.** Config: scrum (step 1) → cook (step 2, fan_out over `{{ steps.scrum.next_targets[0].skills }}`). Forces:
- Slice support in the substitution parser (or at least array-of-strings reading).
- `cook` becoming heartbeat-able (drafts a third `heartbeat.json`; cook is currently `tools/cook_event.py` + `tools/cook_outcome.py` — collectors, not a ritual). May surface that "cook" needs to become an actual ritual skill before fan_out is testable.

Recommend resolving GAP-14 before hand-play 003 (cheap fix: have the gate/idempotency functions read `receipt_dir` from ritual contract). Otherwise three rituals collide on the same scrum-bound functions.

Stopping shadow-design here for operator review of hand-play 002 + closure of GAP-14 before continuing.
