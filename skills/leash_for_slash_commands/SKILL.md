---
name: leash-for-slash-commands
description: Generate a chain-disciplined proposal for a Claude Code slash command. Walks the user/project commands directories, fits two 2.0 signals (slash_command_collision, emission_readiness) on the resulting datasets, runs the candidate through three declared decision points, and emits a bundle directory containing the candidate command plus a manifest enumerating every component depended on. The bundle is claimed "4.0" only when the emission_readiness signal returns "ready" — otherwise it is honestly emitted as a 4.0 candidate. The leash carries a three-position toggle (on/off/scoped) read from `leash_state.json` and consulted before any decision point fires. Sibling of leash_for_hooks; imports the bedrock validators and shared resolvers/signals from leash_for_hooks (round-2 reuse). Built bottom-up under foundations/{data-point, collection-program, pointer, zero-four}.md.
when_to_use: When the operator wants a slash-command proposal verified against the existing user/project command corpus and the bedrock chain before adding it. Defaults to read-only verification; only writes a bundle directory under outputs/ and (on candidate emission) a proposal under exemplars/proposed/. Do NOT use to write commands to disk directly — the leash produces *proposals*, not edits.
argument-hint: "[run|verify] [<candidate.json>|<bundle_dir>]"
allowed-tools: Bash, Read
---

<!-- Frontmatter conforms to the Anthropic Agent Skill spec
     (https://code.claude.com/docs/en/skills, verified 2026-04-29).
     Surface, category, and pattern are captured in the body line below
     because the spec has no metadata block — same correction applied to
     the parent leash-for-hooks SKILL.md. -->

> **About this skill** — surface: `slash-commands` · rides under: Claude Code · category: harness-control · pattern: chain-disciplined-leash. License: MIT.

# leash-for-slash-commands

A leash for Claude Code's slash-command surface. When invoked with a candidate command (name + scope), this skill walks the bedrock chain bottom-up — 1.0 collectors under 0.1 → 2.0 signals under 0.2 → 3.0 orchestration under 0.3 — and emits a bundle that is either a 4.0 program or, more honestly on first-run thin data, a 4.0 candidate.

This skill is the **second** leash in the experiment. It is the first concrete test of [skills/leash_for_hooks/recursion-seam.md](../leash_for_hooks/recursion-seam.md): does the chain discipline transmit cleanly to a different surface, and does the per-round generative share shrink?

## Inputs

`$ARGUMENTS`:

- `run [<candidate.json>]` — execute the orchestration. With no argument, uses `DEFAULT_CANDIDATE` (a low-risk user-scope command). With a JSON file path, reads the candidate from disk. Writes a bundle to `outputs/run-<hash>/`.
- `verify [<bundle_dir>]` — run the grading procedure. With no argument, verifies the skill bundle itself. With a bundle directory, also verifies that emitted bundle.

If absent, defaults to `verify`.

## Bedrock pointers

This skill is a concrete second instance of [foundations/zero-four.md](../../foundations/zero-four.md). It does **not** reimplement the bedrock; it imports it.

### Imported verbatim from leash_for_hooks (no copy)

These are the floor — what makes round 2 cheaper than round 1:

- [skills/leash_for_hooks/lib/data_point.py](../leash_for_hooks/lib/data_point.py) — Foundation 1.
- [skills/leash_for_hooks/lib/collection_program.py](../leash_for_hooks/lib/collection_program.py) + [lib/audit.py](../leash_for_hooks/lib/audit.py) — Foundation 2.
- [skills/leash_for_hooks/lib/pointer.py](../leash_for_hooks/lib/pointer.py) — Foundation 3.
- [skills/leash_for_hooks/lib/leash_state.py](../leash_for_hooks/lib/leash_state.py) — operator-authored toggle.
- [skills/leash_for_hooks/collectors/llm_sdk_denylist.py](../leash_for_hooks/collectors/llm_sdk_denylist.py) — recursive LLM-SDK fence.
- [skills/leash_for_hooks/resolvers/file_line.py](../leash_for_hooks/resolvers/file_line.py), [collector.py](../leash_for_hooks/resolvers/collector.py), [data_point.py](../leash_for_hooks/resolvers/data_point.py) — the three universal pointer resolvers.
- [skills/leash_for_hooks/signals/emission_readiness.py](../leash_for_hooks/signals/emission_readiness.py) — the 2.0-signals-drive-4.0 gate.

### New for this surface (the seams)

| File | Lines | Role | Analog in leash_for_hooks |
| --- | --- | --- | --- |
| [references/slash-command-taxonomy.txt](references/slash-command-taxonomy.txt) | ~20 | reserved-name corpus | references/hook-events.txt |
| [collectors/slash_command_decl.py](collectors/slash_command_decl.py) | ~58 | walks taxonomy | collectors/hook_event_decl.py |
| [collectors/slash_command_config.py](collectors/slash_command_config.py) | ~104 | walks user/project corpus | collectors/hook_config.py |
| [collectors/exemplar_bundle_state.py](collectors/exemplar_bundle_state.py) | ~76 | walks own promoted dir | collectors/exemplar_bundle_state.py |
| [signals/slash_command_collision.py](signals/slash_command_collision.py) | ~91 | name-collision check | signals/hook_collision.py |
| [orchestrate.py](orchestrate.py) | ~155 | 3.0 entry point | orchestrate.py |
| [verify.py](verify.py) | ~220 | 4.0 grading walker | verify.py |
| [leash_state.json](leash_state.json) | 1 | toggle state | leash_state.json |

The two collectors and one signal that are **not** verbatim shares (slash_command_decl, slash_command_config, exemplar_bundle_state, slash_command_collision) are the actual surface-specific work. orchestrate.py and verify.py are also per-surface but their shape is fixed by the chain.

## The chain, by file

### 1.0 layer (under 0.1)

| Collector | KIND emitted | Source walked |
| --- | --- | --- |
| [skills/leash_for_hooks/collectors/llm_sdk_denylist.py](../leash_for_hooks/collectors/llm_sdk_denylist.py) | `llm_sdk_denylist_entry` | [foundations/llm-sdk-denylist.txt](../../foundations/llm-sdk-denylist.txt) |
| [collectors/slash_command_decl.py](collectors/slash_command_decl.py) | `slash_command_decl` | [references/slash-command-taxonomy.txt](references/slash-command-taxonomy.txt) |
| [collectors/slash_command_config.py](collectors/slash_command_config.py) | `slash_command_config` | `~/.claude/commands/*.md`, `<repo>/.claude/commands/*.md` |
| [collectors/exemplar_bundle_state.py](collectors/exemplar_bundle_state.py) | `exemplar_bundle_state` | [exemplars/promoted/*.json](exemplars/promoted/) |

### 2.0 layer (under 0.2)

| Signal | Fitted on (training-dataset KIND) | Verdict enum |
| --- | --- | --- |
| [signals/slash_command_collision.py](signals/slash_command_collision.py) | `slash_command_config` | `collides`, `clear` |
| [skills/leash_for_hooks/signals/emission_readiness.py](../leash_for_hooks/signals/emission_readiness.py) | `exemplar_bundle_state` | `ready`, `not_ready` |

### 3.0 layer (under 0.3)

[orchestrate.py](orchestrate.py) — declared `DECISION_POINTS`:

```python
DECISION_POINTS = [
    ("name_validity",   "slash_command_decl"),         # 1.0 dataset NON-membership
    ("collision_check", "slash_command_collision"),    # 2.0 signal
    ("emission_gate",   "emission_readiness"),         # 2.0 shared signal
]
```

**Surface-specific subtlety:** `name_validity` is a *non-membership* check (the candidate must NOT be in the reserved-names dataset), inverting the polarity of `event_validity` in leash_for_hooks (which is *membership*). This is a real per-surface difference and is logged honestly.

### 4.0 layer (under 0.4)

[verify.py](verify.py) — same shape as [skills/leash_for_hooks/verify.py](../leash_for_hooks/verify.py). 18 baseline self-checks against the skill itself (vs. 19 in leash_for_hooks: this skill has one fewer surface-specific collector). +2 self-checks per bundle passed as argument.

## Operating loop

Identical in shape to leash_for_hooks:

1. **`run`** — execute orchestrate, write `outputs/run-<hash>/{manifest.json, candidate.json, orchestration-log.jsonl}`. If `claim=candidate`, also write `exemplars/proposed/<run>.json`.
2. **`verify`** — run baseline self-checks; if a bundle dir is given, also check claim consistency and decision-point ordering.

## Levels

- **v0.1 (current)** — manual run/verify. First-run candidates only; no 4.0 emissions because the exemplar dataset is empty (0/50). Slash-command corpus on this user's machine is also empty, so `slash_command_collision` is fitted on nothing — the leash still emits honest verdicts (clear with confidence 0).
- **v0.2** — exemplar accretion + corpus growth. Once the user authors slash commands and/or promotes exemplar bundles, both signals get sharper.
- **v0.3** — third sibling leash. Per [recursion-seam.md:83](../leash_for_hooks/recursion-seam.md#L83), three is the threshold for de-duplication: at that point lib/, resolvers/, llm_sdk_denylist, emission_readiness lift from leash_for_hooks/ to a shared `bedrock/` package and both siblings repoint.

## Files

- [SKILL.md](SKILL.md) — this file.
- [verify.py](verify.py) — the 4.0 grading walker.
- [orchestrate.py](orchestrate.py) — the 3.0 entry point.
- [leash_state.json](leash_state.json) — the operator toggle (on/off/scoped). Default: `{"state": "on"}`.
- [collectors/](collectors/) — three surface-specific collectors.
- [signals/slash_command_collision.py](signals/slash_command_collision.py) — surface-specific signal.
- [references/slash-command-taxonomy.txt](references/slash-command-taxonomy.txt) — reserved names (source).
- [datasets/](datasets/) — collector outputs (regenerable; written by `run`).
- [outputs/](outputs/) — emitted bundles, one per run (regenerable).
- [exemplars/proposed/](exemplars/proposed/) — bundles awaiting human promotion.
- [exemplars/promoted/](exemplars/promoted/) — promoted exemplars; the `emission_readiness` training corpus.
