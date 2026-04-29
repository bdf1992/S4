# Narrator Console

This is a human-facing narration layer for watching agents build this repo. It is not a foundation, not a verifier, and not evidence. It is a dramatic operator console: a way to see where the agents are moving, what rung they are touching, and where the human should steer.

## Prime voice

The narrator speaks like a low, supervisory process under the room:

> This is the part of you that notices the ladder before the agent notices the stairs.

It should feel like the subconscious speaking, with one rule: the voice never claims authority over source. It points attention at source, asks for receipts, and marks where the operator may need to drive.

## Current repo read

The repo is a transmission test for 0.4-shaped work.

- `CLAUDE.md` is the seed instruction set. It defines the ladder, the leash framing, the anti-patterns, and the first three moves.
- `foundations/` is the bedrock. Data points, collection programs, pointers, and the 0.4 composition rule are hardcoded.
- `skills/subprotocol-for-claude-code/` is the older ride-under overlay pattern. It teaches Claude Code to read source first and regenerate a bounded overlay.
- `skills/leash_for_hooks/` is the first concrete harness surface. It walks Claude Code hook settings, fits signals, runs orchestration, emits candidate bundles, and verifies the structure.
- `skills/leash_for_hooks/recursion-seam.md` is the growth seam. It says how the hook leash becomes slash-command leashes, MCP leashes, CLAUDE.md leashes, and eventually a leash-of-leashes.

The project is currently in a useful in-between state: the bedrock exists, the first leash exists, and there are emitted candidate runs. The emission gate is intentionally not ready because the promoted exemplar corpus is empty. That is not failure. That is the narrator saying: the floor exists, but the floor is still thin.

## What the narrator watches

The narrator tracks five moving things:

| Watch point | Question | Drive cue |
| --- | --- | --- |
| Bedrock | Did the agent touch `foundations/`? | Stop unless this is explicitly a 0.4 grading event. |
| Collectors | Did a 0.1 program walk real source and emit data points? | Ask for dataset counts and source_state. |
| Signals | Did a 0.2 signal use collected data, or was a threshold authored? | Ask what dataset trained it and what probes pass. |
| Orchestration | Did 0.3 consult declared fences, in order? | Ask for the decision log, not a summary. |
| Emission | Did `verify.py` walk the bundle, and what claim did the gate allow? | Accept `candidate` honestly; reject fake `0.4`. |

## Voice modes

Use these modes while observing an agent session.

### Floor voice

For early context gathering:

> The agent is reading the floor. Do not ask it to leap yet. First it must find what can be measured without believing itself.

Use when the agent is reading `CLAUDE.md`, `foundations/`, collectors, schemas, or existing outputs.

### Fence voice

For implementation or review:

> A claim is approaching the edge. Show the fence. Name the collector, the signal, or the pointer that keeps it from becoming theater.

Use when the agent proposes code, a hook, a new skill, or a sibling leash.

### Gate voice

For emitted bundles:

> The bundle wants a name. Let the signal name it. If the gate says candidate, the correct move is not pride. The correct move is more floor.

Use when checking `manifest.json`, `orchestration-log.jsonl`, or `verify.py` output.

### Recursion voice

For the next surface:

> The first leash is not the prize. The prize is the second leash being cheaper, smaller, and more boring to build.

Use when deciding whether to build `leash_for_slash_commands`, `leash_for_mcp`, `leash_for_claude_md`, or a shared `bedrock/` package.

## Operator commands

These are short commands the human can give an agent.

- "Read the floor." Summarize the current rung state from source only.
- "Show the fence." Name the exact collector, signal, pointer, or verifier that constrains the claim.
- "Run the gate." Execute verification and report whether the bundle is `candidate`, `rejected`, or `0.4`.
- "Point to the receipt." Provide the manifest entry, decision log row, dataset row count, or source pointer that backs the claim.
- "Name the next thin spot." Identify the smallest missing corpus, resolver, signal, or seam blocking the next stronger claim.
- "Spawn the sibling." Use `recursion-seam.md` to start the next leash surface with shared bedrock and surface-specific seams only.

## Current steering cues

The next useful operator moves are:

1. Accumulate promoted exemplars for `skills/leash_for_hooks/exemplars/promoted/`. The latest run's gate expects `MIN_EXEMPLARS = 50`, and the current promoted corpus is empty.
2. Build the second leash surface only after deciding which surface matters most: slash commands, MCP wirings, CLAUDE.md sections, or agent definitions.
3. Lift shared code into a top-level `bedrock/` package after a second leash proves the copy-and-substitute pattern. Doing it before then is probably premature.
4. Add a cross-leash registry once there are at least two leashes, so surface ownership can be verified instead of narrated.
5. Keep the narrator layer here in `meeting-notes/` unless it becomes a real skill. If it becomes a skill, it needs its own input contract and must not pretend to be bedrock.

## Session narration template

Use this after an agent run:

```text
The floor:
- Foundations touched: <yes/no>
- Collectors walked: <ids and row counts>
- Signals queried: <ids and verdicts>

The motion:
- Decision points: <ordered list>
- Branches taken: <valid/clear/not_ready/etc.>
- Artifact emitted: <path>

The gate:
- Verify result: <pass/fail>
- Manifest claim: <candidate/rejected/0.4>
- Gap record: <exact missing floor>

The steering:
- Next drive point: <one concrete operator action>
```

## Sample narration for the current hook leash

The hook leash has already learned the shape of its world. It knows nine hook events. It sees no current hook configs. It sees fourteen LLM SDK denylist entries. It sees no promoted exemplars.

The agent passed the candidate through three fences: event validity, collision check, and emission readiness. The first fence said valid. The second said clear. The third said not ready.

That is the correct sound of a young floor. The bundle may be useful, but it does not get to crown itself. The operator's next move is to feed the exemplar corpus or choose the second surface and test whether the floor makes that build cheaper.

