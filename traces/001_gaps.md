# Hand-play 001 — gaps surfaced

**Trace:** [`runner_trace.jsonl`](runner_trace.jsonl) line 1 (`trace:001`)
**Config:** [`heartbeats/scrum_only.toml`](../heartbeats/scrum_only.toml) — smallest case, single ritual, no fan_out, no loop.
**Ritual contract drafted:** [`.claude/skills/scrum/heartbeat.json`](../.claude/skills/scrum/heartbeat.json)
**Receipt produced:** [`heartbeats/receipts/scrum/2026-05-03-handplay.md`](../heartbeats/receipts/scrum/2026-05-03-handplay.md)

**Source state at hand-play:**
- git HEAD: `b7be123c19ac6577f16ab86e4c63f636fa65e2a3`
- floor signal: `sha256:ea6989183963ab470ea18f22211aa7de`
- cook_outcome: `sha256:1fe379486c7dfbac6e77709d57c20334`

**Decision-step ratio:** 3 deterministic / 10 total (steps 1, 3, 8). The other 7 required judgment because contract or runner primitives don't exist yet. **That ratio IS the spec gap.** A 1.0 runner authored today would have to encode 7 judgment calls as fixed rules.

---

## Gaps, by severity

### Class A — load-bearing primitives missing (block runner authoring)

**GAP-2 / GAP-3 — symbol-pointer kind has no resolver and no target format.**
[`foundations/pointer.md`](../foundations/pointer.md) lists `symbol` as a valid `kind` but only itemizes `file_line`'s target format. No `symbol_resolver` collector exists in the repo. Every pointer in `heartbeat.json` (gate, idempotency, output_writer) is `kind=symbol` and therefore unresolvable.
*Resolution path:* either (a) add a symbol-target appendix to Foundation 3, then write `skills/<x>/collectors/symbol_resolver.py`, OR (b) restrict heartbeat pointers to `kind=file_line` and use `path:line` for everything (cheaper but uglier).

**GAP-7 / GAP-8 — no structured output exists for any current ritual.**
[`tools/standup.py`](../tools/standup.py) emits markdown only. The structured data (commits, cooks, floor signal, ranked candidates) is computed inside `render()` but never exported. `{{ steps.scrum.next_targets }}` substitution from the heartbeat-pattern proposal is impossible against the current ritual.
*Resolution path:* smallest fix is `--emit-structured PATH` flag on standup.py that writes JSON sidecar keyed by same source_state as the markdown. Schema lives at `schemas/scrum_output.json`. **This is the prerequisite for the scrum→cooks×10 example in the proposal.**

**GAP-4 — gate functions don't exist as `should_fire(state) -> bool` shape.**
The proposal's contract requires `gate_pointer` to resolve to `should_fire(state) -> bool`. Existing helpers like `_commits_in_window` are list-returning, not boolean predicates. New code is required *inside the ritual's source* before any heartbeat can fire.
*Resolution path:* add `tools.standup.heartbeat_gate(state) -> bool` (and equivalent for every retrofit candidate). One function per ritual, ≤20 lines each.

### Class B — bootstrap & state shape (block first tick)

**GAP-6 — first-tick bootstrap unspecified.**
Gate `commits-since-last-fire > 0` is undefined when no prior receipt exists. Three possible rules: (a) always fire on first tick, (b) treat absence-of-receipt as `last_fire = beginning-of-time`, (c) require operator to seed an initial receipt. Proposal doesn't pick one.
*Resolution path:* pick (b) — it's the only rule that doesn't require either special-casing in every gate or operator action. Document in proposal under a new "Bootstrap rules" section.

**GAP-5 — idempotency key shape interacts with window-spec.**
For scrum the natural key is `git HEAD + window-spec`, but window for a heartbeat-fired scrum is `since last fire`, not `7d`. The window depends on prior receipts, so the key depends on prior receipts too — recursive.
*Resolution path:* break the recursion by defining heartbeat-fired window as `[last_fire_iso, now]` (closed interval over receipt timestamps, not over a relative spec). Idempotency key becomes `sha256(git_head || last_fire_iso)`.

**GAP-1 — contract location is ambiguous (skills/ vs .claude/skills/).**
Scrum lives at `.claude/skills/scrum/` (slash-command shim only). Most other rituals live at `skills/<name>/` (directly invocable). The runner's discovery rule must walk both, OR the proposal must pick one canonical location and require slash-command rituals to mirror.
*Resolution path:* canonical location is wherever `SKILL.md` sits. Runner walks `**/heartbeat.json`. Cheap, no duplication.

### Class C — schema/storage tradeoffs (don't block but need decision)

**GAP-9 — `receipt_dir` collides with `.gitignore`.**
Default `.claude/skills/<x>/heartbeat_receipts/` lands under `.claude/`, which is gitignored as local state. Receipts are 1.0 datapoints — they MUST be tracked.
*Resolution path:* move receipts to top-level `heartbeats/receipts/<ritual_id>/`. Already created in this hand-play. Update proposal to reflect.

**GAP-10 — `dispatch_surfaces_supported` enum doesn't distinguish "safe under" from "wants".**
Listing `loop` as supported for scrum is wrong — scrum is read-only and *can survive* loop dispatch but doesn't *want* re-entry. Conflating these means the proposal's surface check at config-load time gives the wrong answer.
*Resolution path:* split the field into two: `dispatch_surfaces_safe` (subset rule applies) vs `dispatch_surfaces_recommended` (operator hint). Or drop `loop` for read-only rituals entirely.

**GAP-11 — `audit_budget_lines` doesn't compose across symbols sharing a module.**
Proposal says budget covers gate + output_writer source files combined. For scrum both functions would live in `tools/standup.py` (already 450 lines). Either extract to a separate file per ritual, or budget per-symbol (AST-walk based) instead of per-file.
*Resolution path:* per-symbol budget. AST-walk the named symbol, count substantive lines under it. Already the right rule for shared modules.

### Class D — meta gaps (the trace itself surfaced these)

**GAP-config_hash** — no canonical TOML hash function declared. `config_hash` is null in trace.

**GAP-source_state_composite** — every collector reports its own source_state. Runner needs either a composite (concat hashes) or designate one as primary. Trace records all three for now.

**GAP-receipt_vs_trace** — in the hand-play, this `runner_trace.jsonl` record IS the receipt. The proposal treats them as separate (trace = runner's audit log; receipt = ritual's fire-event record). Need to clarify whether trace records replace per-ritual receipts or augment them.

---

## What this hand-play validated

- **Scaffolding feasibility.** Smallest end-to-end heartbeat is implementable today: config (~10 lines), contract draft, run composer, write receipt. The shape is right.
- **Gap density per class.** 11 gaps from one ritual, simplest config, no fan_out. Pattern proposal is ~70% spec, ~30% load-bearing-prereqs-not-yet-built.
- **Trace shape stability.** The 10-step decision sequence is reusable as the runner's tick loop. Steps 1, 3, 8 are immediately codifiable as 1.0. Steps 2, 4–7, 9, 10 codify only after the gaps in their respective classes close.

## What this hand-play did NOT exercise

- Fan-out (need a config with `[[step]]` × 2)
- `loop = true` re-entry
- Parameter substitution `{{ steps.<id>.<field> }}`
- `scheduled-remote` dispatch surface
- Subagent dispatch concurrency / aggregation

These are the next hand-plays. Each will surface its own gap class. Recommend not authoring the runner until at least hand-play 003 (which exercises substitution) closes the structured-output gap (GAP-7/8) — substitution is impossible without it.

## Suggested next move

**Hand-play 002:** add a second step to `scrum_only.toml` that depends on scrum's structured output. This forces a real fix to GAP-7/8 (or proves they're blockers) before any runner code is written. Candidate: `scrum → render_proposals` (fan_out=1, args interpolate scrum's `next_targets`).

Stopping the shadow-design here for operator review of the gap classes before continuing.
