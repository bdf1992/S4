# Overlay Template — Claude Code

This file documents the structure of the marker-bounded SubProtocol overlay region in a project's `CLAUDE.md`. `sync.py` uses this template (and the section taxonomy) to compose the actual overlay text. The template is rendered with `{key}` substitutions from `references/domain-configuration.yaml`.

The overlay region is bounded by exact-string markers. Both must be present, on their own lines, with no text after the markers on those lines:

```
<!-- SUBPROTOCOL:OVERLAY:START — generated, do not edit between markers -->
...
<!-- SUBPROTOCOL:OVERLAY:END -->
```

`sync.py` finds these by literal-string match. If markers are missing, it appends them at end of file with a freshly generated body. Hand-edits between the markers are clobbered by the next sync.

## Composition order

Slot ordering inside the overlay matches Claude Code's own opening sequence (per the directed-graph convergence noted in [system-prompt-shape](../system-prompt-shape/data/label-graph.md)) and host-anchored slot positions for the rest. Internal order:

1. Header — what this region is, when it was generated, where edits should go.
2. Slot 16 (`repo-customization-protocol`) — declares the overlay attachment in Claude Code's own register; null in body since this slot's role is structural.
3. Slot 2 (`engineering-task-discipline`) — the densest universal slot. Source-first task discipline rendered in Claude Code's `# Doing tasks` register.
4. Slot 3 (`tool-use-discipline`) — pointer-lookup tool invocation in Claude Code's `# Using your tools` register.
5. Slot 4 (`autonomy-and-action-discipline`) — risk-aware source-walk before risky actions, in Claude Code's `# Executing actions with care` register.
6. Slot 5 (`git-rules`) — pointer-form commit messages and PR evidence, in Claude Code's `# Committing changes with git` register.
7. Slot 7 (`formatting-and-output-style`) — pointer-form citation in `# Tone and style` register; merges into Claude Code's existing rules rather than creating a new section.
8. Slot 8a (`host-templated-data-runtime`) — substrate keys for Claude Code's `# Environment` injection.
9. Slot 9 (`tool-spec-catalog`) — SubProtocol tool specs in Claude Code's per-tool `## ToolName` + JSON schema fence format.
10. Slot 10 (`agent-tool-discipline`) — subagent context-publish bullets in Claude Code's `## Agent` register.
11. Slot 11 (`memory-subsystem`) — pointer-form memory rules in Claude Code's `# auto memory` register.
12. Slot 13 (`planning-procedure`) — source-walk-first plan steps for Claude Code's TodoWrite flow.
13. Slot 14 (`context-management`) — substrate-recompute rules in Claude Code's `# Context management` register.
14. Slot 15 (`domain-task-aesthetic`) — design-asset registry lookup; rendered only if the user's domain has design assets.
15. Slot 18 (`request-routing-rules`) — keyword routing for SubProtocol-recognized triggers.
16. Slot 20 (`procedure`) — domain procedures with named judgment seams.
17. Slot 21 (`render`) — computed renders triggered by host events.
18. Footer — provenance pointer back to the skill and the configuration file.

NOOP slots (1, 6, 17) are skipped entirely — `change_response: block` means `sync.py` does not write into Claude Code's identity, refusal, or session-meta regions.

## Header template

```markdown
# SubProtocol overlay — Claude Code

**Generated:** {generation_timestamp} by [subprotocol-for-claude-code](.subprotocol/skills/subprotocol-for-claude-code/SKILL.md)
**Source of truth:** `.subprotocol/skills/subprotocol-for-claude-code/references/domain-configuration.yaml` (do not edit this region directly; edit the configuration and re-run `sync`)
**Active slots:** {active_slot_count} of 21 ({noop_count} NOOP, {disabled_count} disabled in this project)

The rules below ride under Claude Code's existing prompt. They never override Claude Code's own discipline; they add SubProtocol behavior in Claude Code's register.
```

## Per-slot body templates

Each slot's `output_template` (from the section taxonomy) is rendered with `{key}` substitutions from `domain-configuration.yaml`, then translated through [`references/translation-map.md`](references/translation-map.md) so internal SubProtocol vocabulary becomes Claude Code's vocabulary.

A canonical rendered body for slot 2 (`engineering-task-discipline`) in Claude Code's register, for the game-team scenario:

```markdown
## Source-first task discipline

- Before generating new code, walk `definitions/` for an existing module matching the task; prefer a `file_path:line_number` pointer to a copy.
- When generating, register the new module under the matching kind (`asset`, `system`, `scene`, `tool`) in `definitions/<kind>/` so subsequent tasks can resolve via pointer lookup.
- IMPORTANT: source-walk happens BEFORE the first edit, not after. If the registry resolves the task, return the pointer in the response and stop.
```

Note the register: `IMPORTANT:` prefix (Claude Code convention), `file_path:line_number` (Claude Code's citation form, not "pointer"), `task` (not "request"), `module` (not "asset" — translated for the game-team domain). Same SubProtocol behavior, Claude Code's vocabulary.

## Footer template

```markdown
---
**Provenance:** every rule above traces to a slot in [`section-taxonomy.md`](.subprotocol/skills/system-prompt-shape/references/section-taxonomy.md), filled by `domain-configuration.yaml`. Run `subprotocol-for-claude-code check` to verify drift; run `subprotocol-for-claude-code sync` to regenerate.
```

## Sync semantics

`sync.py` does the following each run:

1. Read `CLAUDE.md`. If markers absent, append fresh markers + body at end of file.
2. Read `references/domain-configuration.yaml`. Validate against `references/domain-configuration-schema.md`.
3. Walk `../system-prompt-shape/references/section-taxonomy.md`. For each slot:
   - Skip if `change_response: block` (NOOP slots).
   - Skip if not enabled in `domain-configuration.yaml`.
   - Render body per `change_response`:
     - `regenerate` — emit fresh text from `output_template` + fills + translation-map.
     - `alert` — render expected text, diff against existing overlay body for that slot, log drift, do not rewrite.
     - `collect` — gather slot data into the sync record, emit nothing into overlay body.
4. Compose body per the composition order above.
5. Replace text between markers in `CLAUDE.md`. Preserve everything outside markers.
6. Write `reports/sync-{date}.md` with what fired, what changed, what drifted.

## What goes outside the markers

The user's own `CLAUDE.md` content — project conventions, custom instructions, host-specific notes, anything they've authored — lives outside the markers and is never touched by sync. The overlay region is the only SubProtocol-managed space in `CLAUDE.md`.
