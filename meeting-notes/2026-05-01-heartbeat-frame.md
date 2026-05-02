# Meeting — 2026-05-01 (afternoon): heartbeat frame for time-surface harness

**Attendees:** operator (Bdo), agent (Claude Opus 4.7).
**Status:** alignment captured; no skill code written, no foundations changed, no proposal opened. The frame "heartbeat as pulse-substrate for arbitrary time-surface subscribers" replaced the agent's initial "janitor loop" frame. Recorded as design transcript; graduation path named at the bottom.
**Trigger:** T6 — operator-initiated alignment. (Taxonomy in [meeting-schedule.md](meeting-schedule.md).)

This file is a citation, not a data point. No resolver, no source-state, no Foundation-1 schema. Same disposition as [2026-04-29-continuous-process-framing.md](2026-04-29-continuous-process-framing.md) and the other 2026-04-29 notes: a transcript available as future grading-event input if and when a 0.2 signal fires for the time-surface.

## What we discussed

### Thread 1 — the agent's first frame ("janitor") was wrong register

The operator opened: *"dedicate a loop to git and bookkeeping and org routines through a loop, lets discuss and design how and why."* The agent's first design used "janitor leash" as the central frame and laid out scope, output surface, and three design choices around it.

The operator rejected the frame in one sentence: *"janitor is the wrong frame."*

Recovery analysis (agent):
- Janitor implies cleanup-after-the-fact and contract-worker subordination. The work this loop touches — git history, the decision ledger at [approvals/decisions.jsonl](../approvals/decisions.jsonl), the MEMORY index, the approval log, `.source_state` receipts — is **the franchise's books**, not exhaust to be swept. Calling it janitorial recreates the framing the operator's prior course-correction on AI-as-franchise-owner explicitly warns against.
- Janitor frames the loop as a *role*. The work is a *cadence* the franchise owner runs as part of ownership.

### Thread 2 — heartbeat as substrate, not as role

The operator floated: *"heartbeat could be interesting? Then I could put many arbitrary thing that follow the pulse?"*

That second sentence is the load-bearing move. Heartbeat lifts the frame from role to **substrate**: the loop is not a worker doing tasks; it is a pulse the franchise emits, and arbitrary disciplines can subscribe to it. Subscribers are riders, not employees. The pulse is what the operator holds; what rides it is configurable.

This fixes a structural problem the janitor frame was about to introduce — single-purpose loop construction. With heartbeat-as-substrate, the build is *one* leash (the pulse: rate, on/off, scoped) and disciplines plug in over time.

### Thread 3 — the discriminator (what may ride the pulse)

A subscriber must be **periodic, low-stakes, idempotent, and tolerant of skipped or doubled beats**. Anything else needs a leash, not a pulse.

| Rides the pulse | Needs a real leash |
|---|---|
| Receipt-freshness scans (`.source_state`, REVIEW.html vs .md) | Substantive code edits |
| Orphan walks (proposal / candidate / meeting-notes integrity) | Foundation file edits |
| MEMORY.md drift / pointer liveness | Active proposal grading |
| Render-output regen (HTML from MD) | Anything blocking on operator input |
| Pending-proposal status reconciliation | Skill orchestration mid-flight |
| Log rotation (`overnight_log.jsonl`, `decisions.jsonl`) | Commit-button presses (digest yes, push no) |
| Surface inventory walks | One-shot "do this thing" tasks |

The discriminator is load-bearing: a subscriber that violates idempotency or skip-tolerance doesn't belong on the pulse. Push it off; build it as a leashed task.

### Thread 4 — second-order: the pulse log is itself a 1.0 dataset

Every beat writes one record: `{ts, beat_n, subscribers_fired, findings_per_subscriber}`. Over time that log is the franchise's vital signs — busy periods, quiet periods, which subscribers find drift most often, what reconciles fast vs slow. Deterministic source-walk on the writing path; no LLM in the loop on emission. A 0.1-shaped dataset.

The heartbeat earns its number on the chain this way: pulse runs (1.0 collectors firing), pulse log accumulates (0.1-shaped data), eventually a 0.2 model could read its own metabolism — *"entropy ramps after a substantive push"*, *"this surface drifts on a 3-day cycle"* — and feed back into pulse rate. Self-observing without being self-grading; the bedrock holds.

### Thread 5 — recursion-seam: heartbeat is the harness for the temporal surface

[CLAUDE.md](../CLAUDE.md) names Claude Code surfaces (CLAUDE.md, settings.json, slash commands, MCP wirings, hooks, skill folder). Existing harnesses target hooks ([skills/leash_for_hooks/](../skills/leash_for_hooks/)), slash commands ([skills/leash_for_slash_commands/](../skills/leash_for_slash_commands/)), and the symphony ([skills/leash_for_symphony/](../skills/leash_for_symphony/)).

The heartbeat is the harness for a previously-unaddressed surface: **time** — the between-session cadence and the within-session rhythm. Subscribers are skills attached to the time-surface. The leash for this surface is the pulse itself: toggle on/off, scope to a subscriber set, set rate band.

That places heartbeat as a sibling of the existing `leash_for_*` skills, not a child of any of them. Same recursion property: it must carry the capacity to produce *more* harnesses for sibling surfaces.

### Thread 6 — registration default (declarative for v0)

The agent posed the design question that crystallizes the rest: subscriber registration **declarative** (one `subscribers.yaml`, scanned at boot) vs **self-registering** (each skill drops a `pulse.json`, heartbeat scans skill folders).

The operator's *"ok"* did not pick explicitly. Per the auto-mode + reversible-action default, the agent records the defensible pick: **declarative for v0**. Operator-readable at a glance, single file to leash, easier to verify. Self-registration can come later if a skill needs to travel to a sibling harness. The choice is reversible until a `verify.py` is written against one shape.

## Graduation path — what would move this from meeting-note to proposal

No proposal without a measured gap. The heartbeat does not yet have one. To graduate:

1. Write a `drift_accumulation` gap collector under [skills/gap_audit/collectors/](../skills/gap_audit/collectors/). Walks the repo and emits one data point per detected drift instance: file uncommitted past threshold, MEMORY index pointer dangling, `.source_state` stale against current source, render-output older than source MD. Deterministic, no LLM. Sibling shape to [skills/gap_audit/collectors/surface_inventory_absence.py](../skills/gap_audit/collectors/surface_inventory_absence.py) and the other gap collectors.
2. Run it at a current `source_state`; capture `.jsonl` and `.source_state`.
3. The cited gap pointers become `gap_pointers` in a `prop_2026-MM-DD_heartbeat-for-time-surface/proposal.json`. The candidate — a heartbeat skill that runs subscribers and emits a pulse log — closes them by causing cited drift instances to no longer fire on a future source_state.
4. Foundation-2 pre-verification runs over the candidate. Operator decides.

Steps 1–4 are not authorized by this meeting note. The note authorizes only the heartbeat *frame* and the *registration default*.

## Open threads

- **Registration default review.** Declarative was picked as defensible default; if operator prefers self-registering, flip before any `verify.py` is drafted. *Re-trigger:* any session that begins drafting heartbeat code.
- **Pulse rate band.** Resting ~30 min was floated, not committed. *Re-trigger:* same.
- **Subscriber set for v0.** Seven candidate subscriber classes named in Thread 3; v0 should ship with a small subset (2–3) and grow. Specific picks deferred. *Re-trigger:* same.
- **Sibling-surface order.** Heartbeat is the next sibling harness after `leash_for_symphony`. The surface *after* heartbeat is unspecified. *Re-trigger:* heartbeat ships and operator wants to pick the next surface.

## Operator takeaways

*(Block reserved for operator. Notes-of-record from this meeting, if any, get added by the operator after-the-fact.)*
