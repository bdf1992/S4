# Meeting Schedule

A scaling pattern for when meetings happen in this experiment, what triggers them, what they capture, and how the pattern grows over rounds. Peer to [narrator-console.md](narrator-console.md): a non-dated process artifact, not a foundation, not a verifier, not evidence. The narrator console says *how the operator watches an agent session*. This file says *when operator and agent convene a session in the first place, and how those sessions accumulate into a corpus*.

The agent (Claude Opus 4.7) authored this on 2026-04-29 at the operator's delegation. The pattern is sub-to-source: it formalizes what is already happening (four meeting notes accumulated on a single day under no explicit schedule) rather than inventing new shape.

## What a "meeting" is here

A meeting is a structured operator+agent session that produces a meeting note. It is not a calendar event. It does not require both parties to be co-present in real time. The minimum viable meeting is a single conversation turn that produces a captured note; the maximum is a multi-thread session like [2026-04-29-receipts-and-existing-structure.md](2026-04-29-receipts-and-existing-structure.md).

A meeting always produces a meeting note. A note without a meeting is a citation; a meeting without a note is unrecorded and may as well not have happened.

## Why event-driven, not calendar-driven

The experiment's bedrock is signal-driven: things ship when 0.2 signals fire, not when requests arrive ([foundations/zero-four.md:178](../foundations/zero-four.md#L178)). A calendar-cadence meeting schedule would manufacture meeting substance on a clock and pull the discipline back toward request-driven scaffolding. That is the failure mode the foundations are written to catch.

Event-driven means: a meeting happens when a trigger condition fires. If no trigger fires, no meeting is owed. The schedule is the trigger taxonomy below, not a calendar.

A floor cadence (not a ceiling) is included as one of the triggers, so that long silences do not let open threads rot unread. That floor is 14 days, configurable downward by the operator if the leash count grows past two.

## Trigger taxonomy

Each meeting note declares one trigger in its frontmatter. The taxonomy is fixed up front (per the foundations rule that kinds are declared once and grown by addition, not by mutation):

| ID | Trigger | When it fires | Prior-art note |
| --- | --- | --- | --- |
| **T1** | Alignment thread did not converge in-conversation | An operator+agent exchange surfaces a thread that does not reduce to existing structure within the conversation itself. The note captures the unconverged substance. | [2026-04-29-receipts-and-existing-structure.md](2026-04-29-receipts-and-existing-structure.md), [2026-04-29-continuous-process-framing.md](2026-04-29-continuous-process-framing.md) |
| **T2** | Pre-decision moment for a 0.4 grading event | A foundation change is being considered. Note captures the proposal, the rejected/accepted decision, and the re-trigger condition. | [2026-04-29-handoff-event-001-decision.md](2026-04-29-handoff-event-001-decision.md), [foundations/grading-events.md](../foundations/grading-events.md) |
| **T3** | Post-leash decision | A leash has shipped or stalled and the next leash surface is being chosen. Note captures the surface options and the choice. | [skills/leash_for_hooks/recursion-seam.md](../skills/leash_for_hooks/recursion-seam.md) |
| **T4** | Modal-force / backlog reconciliation | The agent and operator reconcile what is being deferred, what is open, what is parked. Distinct from T1 because the substance is *the project state*, not a single thread. | [2026-04-29-modal-force-and-backlog.md](2026-04-29-modal-force-and-backlog.md) |
| **T5** | Agent-initiated stop-and-report | The agent invokes one of the CLAUDE.md "Stop and report" conditions: foundation pressure, anti-pattern drift, rung-skipping pressure, end-of-move checkpoint. | [CLAUDE.md](../CLAUDE.md) Stop-and-report section |
| **T6** | Operator-initiated alignment | The operator wants alignment on something the agent has not surfaced. Note captures the operator's question and the agent's response, even if no thread is unresolved at the end. | (any future operator-driven session) |
| **T7** | Floor cadence (14 days max) | More than 14 days have elapsed since the last meeting note. The floor cadence meeting may report "no open threads" and remain shippable; this is itself useful data about silence intervals. | (none yet — first floor would fire 2026-05-13 if no other trigger fires before then) |

Adding a new trigger is a structural change and should itself be a meeting note (T1). Removing one requires evidence that the trigger never fires; do not remove on aesthetic grounds.

## Note format

Every meeting note declares, at minimum:

```markdown
# Meeting — YYYY-MM-DD (<rough time-of-day for disambiguation>)

**Attendees:** operator (<name>), agent (<model + version>).
**Status:** <shippable | alignment | floor-cadence-no-substance>
**Trigger:** <T1..T7>
```

Followed by:
- **Disposition declaration.** Citation vs. data-point status. By default a meeting note is a citation, not a data point — no Foundation-1 schema, no resolver, no source-state. If a meeting note is being authored as a data point (e.g., the substance is a probe result), declare the kind and the resolver explicitly.
- **What we discussed.** One section per thread. Threads are numbered.
- **Why nothing shipped** (if status is `alignment` or `floor-cadence-no-substance`). Names what would have to fire for the substance to ship.
- **Open threads.** Unresolved items, with re-trigger conditions. Either side may pull.
- **Agent takeaways.** What the agent updated about its own operating discipline based on the session.
- **Operator takeaways.** Reserved as `*(open — fill in or leave blank)*`. The operator may write or leave empty; either is a legitimate state.

This format is descriptive, not prescriptive — it codifies what the existing notes already do. Variations (tables, voice modes from [narrator-console.md](narrator-console.md), embedded diagrams) are fine when they serve the substance.

## Naming convention

- Dated alignment captures: `meeting-notes/YYYY-MM-DD-<short-hyphenated-topic>.md`. Multiple notes on one day are allowed; the topic disambiguates. Example: `2026-04-29-continuous-process-framing.md`.
- Non-dated process artifacts (this file, [narrator-console.md](narrator-console.md)): `meeting-notes/<descriptive-name>.md`, no date. These are reference artifacts, not session captures.

A note's filename is permanent once committed. Renames are allowed only if the topic was misnamed at creation; never as housekeeping.

## Scaling phases

The pattern grows in phases. Do not skip ahead; do not invent shape before its phase fires.

### Phase 0 — current state

- Convention is informal. Four notes from one day demonstrate the format works.
- Triggers are implicit and documented here (T1..T7). Notes may be authored without declaring trigger ID; backfilling is allowed.
- No tooling. Notes are hand-authored markdown.

### Phase 1 — explicit triggers, no automation

- Every new note declares its trigger ID in the header. The four 2026-04-29 notes can be backfilled if convenient; not required.
- Floor cadence (T7) becomes operator-initiated. The agent does not nag.
- Still no tooling.

This phase fires once the pattern in this file is approved by the operator. Marker for entry: a meeting note (T1) that ratifies this file's pattern, or a single-line operator approval recorded in the note's `Operator takeaways` block.

### Phase 2 — recurring meeting types productize as templates

- If a recurring trigger pattern emerges (e.g., T3 post-leash decisions happen 5+ times with the same sub-structure), a template lives at `meeting-notes/templates/<trigger-id>.md`.
- Templates are descriptive scaffolding, not validators. A note may deviate from a template; the template is a starting point.
- Trigger condition for entering this phase: 5+ notes of the same trigger type, OR an operator decision that template scaffolding would help.

### Phase 3 — leash for the meeting-notes surface

- The meeting-notes/ directory becomes a Claude Code surface in the same sense as settings.json (hooks) and slash commands. A leash for it ([skills/leash_for_meeting_notes/](../skills/leash_for_meeting_notes/)) is built under [recursion-seam.md](../skills/leash_for_hooks/recursion-seam.md).
- The leash emits structured meeting notes the way the hooks leash emits settings.json fragments: 0.1 collectors walk the existing notes, 0.2 signals fit on trigger-frequency and convergence patterns, 0.3 orchestration drafts new notes from a trigger ID and operator-supplied substance, `verify.py` walks the bundle.
- Trigger condition for entering this phase: 5+ template-conformant notes of at least 2 distinct trigger types, AND the second leash (slash commands or other) has shipped, AND the operator decides the meeting-notes surface is the next leash target. *All three conditions* — under-shooting any one is premature.

Building any later phase before its trigger fires is request-driven scaffolding and a foundations violation. The phases exist to make floor-growth visible across rounds; each phase consumes evidence the previous phase produced.

## Recursion property

This file's existence as a peer to [narrator-console.md](narrator-console.md) demonstrates that `meeting-notes/` is itself a sub-surface of the project. CLAUDE.md says the harness must carry the capacity to produce more harnesses for sibling Claude Code surfaces. Meeting-notes is one such sibling — distinct from settings.json (hooks), slash commands, MCP wirings, and CLAUDE.md sections. When Phase 3 fires, the leash for meeting-notes is built from [recursion-seam.md](../skills/leash_for_hooks/recursion-seam.md) under the same bedrock as the hooks leash.

The recursion is *latent now, real later*. This file does not claim it. It marks the seam where it would attach.

## What this file is *not*

- **Not a foundation.** The bedrock is fixed in [foundations/](../foundations/). This is a process artifact at the same epistemic tier as [narrator-console.md](narrator-console.md).
- **Not a verifier.** No probe runs against this file. A note that violates the pattern is a note that violates the pattern; no `verify.py` exit code is at stake until Phase 3.
- **Not a calendar.** No external scheduler is wired. The `schedule` skill (Claude Code's cron-scheduled remote agents) is *available* if the operator wants T7 floor-cadence reminders automated, but is *not built* under this pattern. Building it is a Phase 2 question and signal-gated.
- **Not authoritative over operator behavior.** The operator may override any trigger, decline any cadence, and reshape the pattern unilaterally. The pattern is a default; the operator holds the leash.

## Open question deferred to operator

- **Should T7's 14-day floor be wired to a scheduled remote agent now, or wait until Phase 2?** The agent's recommendation is *wait*: a 14-day cadence has not yet fired even once, and pre-building the automation is exactly the request-driven scaffolding the bedrock is written to catch. The operator may override by invoking `/schedule` directly when ready.
