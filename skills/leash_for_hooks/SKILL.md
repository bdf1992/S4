---
name: leash-for-hooks
description: Generate a chain-disciplined proposal for a Claude Code settings.json hook. Walks all four standard hook-config scopes (user, user-local, project, project-local), fits two 2.0 signals (hook_collision, emission_readiness) on the resulting datasets, runs the candidate through three declared decision points, and emits a bundle directory containing the candidate hook plus a manifest enumerating every component depended on. The bundle is claimed "4.0" only when the emission_readiness signal returns "ready" — otherwise it is honestly emitted as a 4.0 candidate with a gap_record naming what's missing. The leash carries a three-position toggle (on/off/scoped) read from `leash_state.json` and consulted before any decision point fires, so the operator can disengage the leash on trusted surfaces and tighten it on unfamiliar ones. Built bottom-up under foundations/{data-point, collection-program, pointer, zero-four}.md; produces sibling leashes for other Claude Code harness surfaces under the same skeleton (see recursion-seam.md).
when_to_use: When the operator wants a hook proposal verified against the existing settings.json corpus and the bedrock chain before adding it to settings.json. Defaults to read-only verification; only writes a bundle directory under outputs/ and (on candidate emission) a proposal under exemplars/proposed/. Do NOT use to write hooks to settings.json directly — the leash produces *proposals*, not edits.
argument-hint: "[run|verify] [<candidate.json>|<bundle_dir>]"
allowed-tools: Bash, Read
---

<!-- Frontmatter conforms to the Anthropic Agent Skill spec
     (https://code.claude.com/docs/en/skills, verified 2026-04-29).
     Earlier drafts of this file carried a `metadata:` block with
     author/version/category/pattern/rides_under/surface — none of
     those are recognized fields in the spec. The information that
     was load-bearing (the surface this leash targets) is captured
     in the body below; author/version are git history concerns. -->

> **About this skill** — surface: `settings.json/hooks` · rides under: Claude Code · category: harness-control · pattern: chain-disciplined-leash. License: MIT.

# leash-for-hooks

A leash for Claude Code's `settings.json` hooks surface. When invoked with a candidate hook (event + matcher + command), this skill walks the bedrock chain bottom-up — 1.0 collectors under 0.1 → 2.0 signals under 0.2 → 3.0 orchestration under 0.3 — and emits a bundle that is either a 4.0 program (engineering process fully observable in the artifact) or, more honestly on first-run thin data, a 4.0 candidate with the gap recorded.

This skill rides under Claude Code's prompt and uses Claude Code's vocabulary (`task`, `file_path:line_number`, `TodoWrite`, `IMPORTANT:`). The bedrock terms (data point, collector, pointer, signal, manifest) are operational; the framing matches CLAUDE.md's "agentic leash for Claude Code" deliverable.

## Inputs

`$ARGUMENTS`:

- `run [<candidate.json>]` — execute the orchestration. With no argument, uses `DEFAULT_CANDIDATE` (a low-risk PreToolUse hook). With a JSON file path, reads the candidate from disk. Writes a bundle to `outputs/run-<hash>/`.
- `verify [<bundle_dir>]` — run the grading procedure. With no argument, verifies the skill bundle itself. With a bundle directory, verifies that emitted bundle additionally.

If absent, defaults to `verify`.

## Bedrock pointers

This skill is a concrete instance of [foundations/zero-four.md](../../foundations/zero-four.md) for one harness surface. Every component traces to a foundation:

- [foundations/data-point.md](../../foundations/data-point.md) → [lib/data_point.py](lib/data_point.py)
- [foundations/collection-program.md](../../foundations/collection-program.md) → [lib/collection_program.py](lib/collection_program.py) + [lib/audit.py](lib/audit.py)
- [foundations/pointer.md](../../foundations/pointer.md) → [lib/pointer.py](lib/pointer.py) + [resolvers/](resolvers/)
- [foundations/zero-four.md](../../foundations/zero-four.md) → [verify.py](verify.py) + [orchestrate.py](orchestrate.py)

## The chain, by file

### 1.0 layer (under 0.1)

| Collector | KIND emitted | Source walked |
| --- | --- | --- |
| [collectors/llm_sdk_denylist.py](collectors/llm_sdk_denylist.py) | `llm_sdk_denylist_entry` | [foundations/llm-sdk-denylist.txt](../../foundations/llm-sdk-denylist.txt) |
| [collectors/hook_event_decl.py](collectors/hook_event_decl.py) | `hook_event_decl` | [references/hook-events.txt](references/hook-events.txt) |
| [collectors/hook_config.py](collectors/hook_config.py) | `hook_config` | `~/.claude/settings.json`, `~/.claude/settings.local.json`, `<repo>/.claude/settings.json`, `<repo>/.claude/settings.local.json` |
| [collectors/exemplar_bundle_state.py](collectors/exemplar_bundle_state.py) | `exemplar_bundle_state` | [exemplars/promoted/*.json](exemplars/promoted/) |

Resolvers (also 1.0):

| Resolver | POINTER_KIND |
| --- | --- |
| [resolvers/file_line.py](resolvers/file_line.py) | `file_line` |
| [resolvers/collector.py](resolvers/collector.py) | `collector` |
| [resolvers/data_point.py](resolvers/data_point.py) | `data_point` |

Each collector and resolver passes [lib/audit.py](lib/audit.py) — no LLM-SDK imports, no banned nondeterminism (`random`/`uuid`/`socket`/`time`/`datetime`), under audit budget. The "no LLM" check consumes the data points emitted by `llm_sdk_denylist.py`, not the source file directly — Foundation 2's recursive constraint.

### 2.0 layer (under 0.2)

| Signal | Fitted on (training-dataset KIND) | Verdict enum |
| --- | --- | --- |
| [signals/hook_collision.py](signals/hook_collision.py) | `hook_config` | `collides`, `clear` |
| [signals/emission_readiness.py](signals/emission_readiness.py) | `exemplar_bundle_state` | `ready`, `not_ready` |

Both signals expose `evaluate(input) -> {verdict, confidence, evidence_pointers, ...}` and ship a `PROBES` constant; `verify.py` runs the probes to confirm fit-time behavior holds at verification time.

### 3.0 layer (under 0.3)

[orchestrate.py](orchestrate.py) — declared `DECISION_POINTS`:

```python
DECISION_POINTS = [
    ("event_validity",   "hook_event_decl"),    # 1.0 dataset membership
    ("collision_check",  "hook_collision"),     # 2.0 signal
    ("emission_gate",    "emission_readiness"), # 2.0 signal
]
```

The orchestration consults exactly these fences in this order. `verify.py` structurally checks both the order and the fence identifiers against the source.

Before the decision points, a **toggle gate** (`toggle_check`) consults [leash_state.json](leash_state.json) via [lib/leash_state.py](lib/leash_state.py) and short-circuits to `claim: "unleashed"` when the operator has set the leash off, or scoped-off for this candidate's event. The toggle is operator-authored 1.0 config, not a per-surface decision point — `DECISION_POINTS` stays the per-surface bound and the toggle stays the cross-surface mechanism that recursion-seam.md reuses verbatim.

### 4.0 layer (under 0.4)

[verify.py](verify.py) is the grading walker. It runs steps 2–7 of [foundations/zero-four.md](../../foundations/zero-four.md)'s grading procedure: validates every collector and resolver via Foundation 2, runs every signal's probe set, validates every emitted data point against Foundation 1, structurally inspects orchestration source for declared decision-point coverage, and (when given an output bundle path) checks the bundle's manifest claim consistency and decision-point ordering against its log.

`verify.py` is itself structurally a 1.0 collector (with COLLECTOR_ID, KIND, INPUTS, collect, verify) so it is held to the same Foundation 2 constraints it applies to others.

## Operating loop

1. **`run`** — execute the orchestration:
   - For each collector, compute source_state, walk INPUTS, emit data points, persist to `datasets/<COLLECTOR_ID>.jsonl`.
   - For each signal, fit on its declared training-dataset.
   - For the candidate hook, pass through `DECISION_POINTS` in order; record each consultation as a structured log entry with `(verdict, confidence, evidence_pointers, branch_taken)`.
   - Emit `outputs/run-<hash>/{manifest.json, candidate.json, orchestration-log.jsonl}`.
   - If the emission_readiness verdict was `not_ready`, also write `exemplars/proposed/<run_id>.json` so a later human-in-the-loop step can promote it.
   - The manifest's `claim` is `"4.0"` iff the gate fired; otherwise `"candidate"`. Rejected candidates (unknown event, collision) are claimed `"rejected"`.

2. **`verify`** — run the grading procedure:
   - 18 baseline self-checks against the skill bundle.
   - +N additional self-checks against any specific output bundle passed as the argument.
   - Exit 0 iff every self-check passes. Note: a `not_ready` emission gate **does not fail verify** — it correctly produces a "candidate" claim, which is a legitimate output per [foundations/zero-four.md](../../foundations/zero-four.md).

## Work rules

- **Ride under, never replace.** This skill produces leashes; it does not relitigate Claude Code's existing rules. Hook proposals must conform to Claude Code's settings.json schema, not invent new shapes.
- **Source is first-class.** The corpus walked by collectors is the user's actual settings.json files, not a copy or fixture. Re-running against the same filesystem state must produce a byte-identical dataset modulo advisory `collected_at`.
- **No LLM in the bedrock.** The 1.0 layer (collectors, resolvers, validators) contains no model call. The 3.0 layer can be invoked by an LLM (Claude Code itself), but the orchestration source it executes is not generative — it consults declared fences and branches deterministically.
- **Honest verdicts only.** A first-run leash with no exemplar bundles emits a `"candidate"` claim, not `"4.0"`. Promoting that claim requires real exemplars, accumulated by the human via the promotion protocol in [collectors/exemplar_bundle_state.py](collectors/exemplar_bundle_state.py).
- **Audit budgets are load-bearing.** Collectors ≤ 80 lines of substantive code. Resolvers ≤ 60. Orchestration ≤ 150. Verify ≤ 200. The smallness is what makes a quiet rewrite visible in diff.
- **`MIN_EXEMPLARS = 50`** in [signals/emission_readiness.py](signals/emission_readiness.py) is the only authored number in the bedrock. Everything else is fitted to data. Changing it is a deliberate, file-level edit. (Bootstrap value of 3 was too permissive — a 4.0 claim sitting on 3 exemplars is trivially game-able. 50 fences emission until the corpus is real.)

## Levels

- **v0.1 (current)** — manual run/verify with toggle. The skill is invoked from the command line; outputs are written to disk; promotion of exemplars is a manual file-copy step. One harness surface (`settings.json` hooks). Toggle (on/off/scoped) honored via leash_state.json. First-run candidates only; no 4.0 emissions yet because the exemplar dataset is empty.
- **v0.2** — exemplar accretion. Once `exemplars/promoted/` has ≥ `MIN_EXEMPLARS` entries (currently 50), `emission_readiness` can fire `ready` and bundles can claim `"4.0"`. The leash is invoked across more candidate hooks; the dataset of `hook_config` data points grows as users configure more hooks; collision signals get sharper.
- **v0.3** — sibling leashes. The skeleton in this skill spawns leashes for other Claude Code harness surfaces (slash commands, MCP wirings, CLAUDE.md sections, agent definitions). Each new leash bedrock-conforming under the same rules; the foundations/ directory is shared. See [recursion-seam.md](recursion-seam.md).

## Toggle (leash_state)

[leash_state.json](leash_state.json) carries the operator's toggle for this surface. Three states (per [CLAUDE.md:26](../../CLAUDE.md#L26)):

| State | Meaning | Effect |
| --- | --- | --- |
| `"on"` | Leashed by default. | Every candidate runs through every declared decision point. |
| `"off"` | Disengaged. | Candidates pass through; claim is `"unleashed"`. No surface decision points consulted. |
| `"scoped"` | Per-event toggle. | Leashed for events listed in `scoped_on_events`; unleashed for everything else. |

Examples:

```json
{ "state": "on" }
{ "state": "off" }
{ "state": "scoped", "scoped_on_events": ["PreToolUse", "UserPromptSubmit"] }
```

Default committed value is `"on"` — the safe default. Weakening to `"off"` or `"scoped"` is a deliberate operator action. The state is recorded in every emitted bundle's manifest.

## Files

- [SKILL.md](SKILL.md) — this file.
- [verify.py](verify.py) — the 4.0 grading walker.
- [orchestrate.py](orchestrate.py) — the 3.0 entry point.
- [leash_state.json](leash_state.json) — the operator toggle (on/off/scoped).
- [recursion-seam.md](recursion-seam.md) — how this leash spawns siblings.
- [lib/](lib/) — Foundation 1/2/3 implementations + `leash_state.py` (shared toggle validator).
- [collectors/](collectors/) — 1.0 source-walking programs.
- [resolvers/](resolvers/) — 1.0 pointer-resolution programs.
- [signals/](signals/) — 2.0 fitted-on-data-points functions.
- [references/hook-events.txt](references/hook-events.txt) — canonical hook-event taxonomy (source).
- [datasets/](datasets/) — collector outputs (regenerable; written by `run`).
- [outputs/](outputs/) — emitted bundles, one per run (regenerable).
- [exemplars/proposed/](exemplars/proposed/) — bundles awaiting human promotion.
- [exemplars/promoted/](exemplars/promoted/) — promoted exemplars; the `emission_readiness` training corpus.
