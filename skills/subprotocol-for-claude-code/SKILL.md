---
name: subprotocol-for-claude-code
description: Generate and maintain a SubProtocol overlay block inside a project's CLAUDE.md so that Claude Code reads SubProtocol behavior in Claude Code's own register. Use when a team wants Claude Code to walk a registry before generating, cite by pointer, regenerate computed renders on demand, or run domain procedures with named judgment seams. The overlay text is regenerated from `references/domain-configuration.yaml` plus the section taxonomy in [system-prompt-shape](../system-prompt-shape/SKILL.md); do not hand-edit the overlay region in CLAUDE.md.
license: MIT
metadata:
  author: SubProtocol
  version: 0.1.0
  category: workflow-automation
  pattern: substrate-generation
  framing: per-host-overlay
  rides_under: claude-code
---

# SubProtocol for Claude Code

Generate the SubProtocol overlay block in a project's `CLAUDE.md`. The overlay is a regenerable, marker-bounded region that adds SubProtocol behavior (source-first lookup, pointer-form citation, registry coordination, computed renders, named procedures) to Claude Code's existing prompt without touching anything outside the markers.

This skill rides under Claude Code's prompt — it never replaces, never relitigates, and uses only Claude Code's vocabulary (task, file_path:line_number, TodoWrite, IMPORTANT:, etc.). SubProtocol's abstract terms (asset, pointer, kind, definition) stay internal; the overlay text translates them through [`references/translation-map.md`](references/translation-map.md).

## Inputs

`$ARGUMENTS` — the operation to perform:

- `setup` — first-time setup. Runs the LLM-assisted interview at [`scripts/setup-interview.py`](scripts/setup-interview.py) against the existing CLAUDE.md and repo, proposes a `references/domain-configuration.yaml`, and writes the initial overlay block.
- `sync` — regenerate the overlay from current source. Runs [`scripts/sync.py`](scripts/sync.py); rewrites only the marker-bounded region. Default operation; suitable for a git pre-commit hook.
- `check` — read-only drift check. Renders what the overlay should be, diffs against the current overlay region, exits non-zero on drift. Suitable for CI.
- `add-slot <slot-name>` — opt a slot into the active overlay. Looks up the slot in the section taxonomy, prompts for required `domain_configuration` fills, regenerates.

If absent, defaults to `sync`.

## Operating loop

1. **Locate the host customization file.** Slot 16 (`repo-customization-protocol`) names the file: for Claude Code, this is `CLAUDE.md` at repo root. If none exists, [`scripts/setup-interview.py`](scripts/setup-interview.py) creates one.

2. **Read the domain configuration.** [`references/domain-configuration.yaml`](references/domain-configuration.yaml) carries the user's fills for each active slot's `domain_configuration` block (registry path, asset kinds, pointer format, risk classes, procedure kinds, render kinds, etc.). The schema is documented in [`references/domain-configuration-schema.md`](references/domain-configuration-schema.md).

3. **Walk the active slot list.** For each slot in [`../system-prompt-shape/references/section-taxonomy.md`](../system-prompt-shape/references/section-taxonomy.md) where `change_response != block` and the slot is enabled in `domain-configuration.yaml`:
   - Pull the `output_template`.
   - Substitute `{key}` references with values from `domain-configuration.yaml`.
   - Translate any internal SubProtocol vocabulary through [`references/translation-map.md`](references/translation-map.md) into Claude Code's register.
   - Anchor at the slot's `host_anchor.claude-code` location (most slots append into the SubProtocol overlay region; slot 7's citation rules merge into Claude Code's existing tone-and-style block, etc.).

4. **Compose the overlay block** per the structure in [`overlay.md`](overlay.md). Section order follows slot ordering observed in Claude Code (per the directed graph in [`../system-prompt-shape/data/label-graph.md`](../system-prompt-shape/data/label-graph.md)).

5. **Write between markers.** The overlay is bounded by:

   ```
   <!-- SUBPROTOCOL:OVERLAY:START — generated, do not edit between markers -->
   ...generated content...
   <!-- SUBPROTOCOL:OVERLAY:END -->
   ```

   `sync.py` rewrites only between these markers. Everything else in `CLAUDE.md` (the user's hand-authored sections, top-of-file conventions, custom instructions) is preserved.

6. **Apply per-slot `change_response`.** For slots with `regenerate` (the default), the overlay text is replaced wholesale. For `alert`, drift is logged but the overlay is left alone. For `collect`, the slot data is gathered into a report at `reports/sync-<date>.md` but no overlay text is emitted. For `block`, the slot is skipped entirely (NOOP slots — persona, refusal, session-meta).

7. **Emit a sync record.** `reports/sync-<date>.md` lists which slots fired, which `change_response` modes triggered, what changed, and any drift detected. The record is regenerable; do not hand-edit.

## Work rules

- **Ride under, never replace.** The overlay never overrides Claude Code's own rules; it only adds SubProtocol behavior in Claude Code's register. If the overlay would conflict with a Claude Code rule, the slot adapter must say so (or the slot is wrong for this host).
- **Use Claude Code vocabulary only.** Overlay text says `task`, `file_path:line_number`, `TodoWrite`, `CLAUDE.md`, `IMPORTANT:` — not `request`, `pointer`, `asset`, `registry`. The translation happens in render, not in user-facing prose. The bridge is in [`references/translation-map.md`](references/translation-map.md).
- **Regenerate, do not author.** Overlay text is computed from `domain-configuration.yaml` plus the taxonomy. Hand-edits inside the markers are clobbered by the next `sync`. If a fill is wrong, edit `domain-configuration.yaml` and re-sync.
- **Markers are load-bearing.** Both the START and END markers must be exact strings — `sync.py` finds them by literal match. Renaming or deleting a marker turns sync into a no-op (or a clobber, depending on the operation). The setup interview installs the markers; do not move them.
- **Source-first inside the overlay too.** Every behavior the overlay describes is grounded in either (a) a slot in `section-taxonomy.md`, (b) a SubProtocol principle in memory, or (c) corpus evidence in `system-prompt-shape/data/seed-pass.md`. No bullet appears in the overlay without traceable provenance.
- **Setup is a skill, not a config dump.** First-time setup runs an interview that reads the existing CLAUDE.md + repo structure and proposes defaults. The user reviews and accepts; they do not write `domain-configuration.yaml` from scratch.

## Levels

- **v0.1 (current)** — manual sync. The user runs `subprotocol-for-claude-code sync` from the skill; the script rewrites the marker-bounded region. One host (Claude Code), one project at a time. Hand-curated fills accepted by the user via the setup interview.
- **v0.2** — automated sync. `sync.py` is wired into a git pre-commit hook. Drift checks run in CI via the `check` operation. Pre-hook injection (`timing: pre`) becomes available for slots that need it.
- **v0.3** — multi-host. Sibling skills `subprotocol-for-codex`, `subprotocol-for-gemini-cli`, `subprotocol-for-jules` reuse the same `domain-configuration.yaml`; only the translation-map and host_anchor mapping change per host. The team's domain knowledge survives a host switch.

## Files

- [`overlay.md`](overlay.md) — overlay template with marker structure and per-slot composition order.
- [`references/translation-map.md`](references/translation-map.md) — SubProtocol-internal → Claude Code register vocabulary bridge.
- [`references/domain-configuration-schema.md`](references/domain-configuration-schema.md) — schema for `domain-configuration.yaml`.
- [`references/domain-configuration.yaml`](references/domain-configuration.yaml) — per-project fills (the user's tuning surface).
- [`scripts/sync.py`](scripts/sync.py) — regeneration program; reads source + config, rewrites between markers.
- [`scripts/setup-interview.py`](scripts/setup-interview.py) — LLM-assisted first-time setup.
