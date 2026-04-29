---
name: leash-for-hooks
description: Generate a ladder-disciplined proposal for a Claude Code settings.json hook. Walks all four standard hook-config scopes (user, user-local, project, project-local), fits two 0.2 signals (hook_collision, emission_readiness) on the resulting datasets, runs the candidate through three declared decision points, and emits a bundle directory containing the candidate hook plus a manifest enumerating every component depended on. The bundle is claimed "0.4" only when the emission_readiness signal returns "ready" — otherwise it is honestly emitted as a sub-0.4 candidate with a gap_record naming what's missing. Built bottom-up under foundations/{data-point, collection-program, pointer, zero-four}.md; produces sibling leashes for other Claude Code harness surfaces under the same skeleton (see recursion-seam.md).
license: MIT
metadata:
  author: zero-four-experiment
  version: 0.1.0
  category: harness-control
  pattern: ladder-disciplined-leash
  rides_under: claude-code
  surface: settings.json/hooks
---

# leash-for-hooks

A leash for Claude Code's `settings.json` hooks surface. When invoked with a candidate hook (event + matcher + command), this skill walks the bedrock ladder bottom-up — 0.1 collectors → 0.2 signals → 0.3 orchestration — and emits a bundle that is either a 0.4 program (engineering process fully observable in the artifact) or, more honestly on first-run thin data, a sub-0.4 candidate with the gap recorded.

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

## The ladder, by file

### 0.1 layer

| Collector | KIND emitted | Source walked |
| --- | --- | --- |
| [collectors/llm_sdk_denylist.py](collectors/llm_sdk_denylist.py) | `llm_sdk_denylist_entry` | [foundations/llm-sdk-denylist.txt](../../foundations/llm-sdk-denylist.txt) |
| [collectors/hook_event_decl.py](collectors/hook_event_decl.py) | `hook_event_decl` | [references/hook-events.txt](references/hook-events.txt) |
| [collectors/hook_config.py](collectors/hook_config.py) | `hook_config` | `~/.claude/settings.json`, `~/.claude/settings.local.json`, `<repo>/.claude/settings.json`, `<repo>/.claude/settings.local.json` |
| [collectors/exemplar_bundle_state.py](collectors/exemplar_bundle_state.py) | `exemplar_bundle_state` | [exemplars/promoted/*.json](exemplars/promoted/) |

Resolvers (also 0.1):

| Resolver | POINTER_KIND |
| --- | --- |
| [resolvers/file_line.py](resolvers/file_line.py) | `file_line` |
| [resolvers/collector.py](resolvers/collector.py) | `collector` |
| [resolvers/data_point.py](resolvers/data_point.py) | `data_point` |

Each collector and resolver passes [lib/audit.py](lib/audit.py) — no LLM-SDK imports, no banned nondeterminism (`random`/`uuid`/`socket`/`time`/`datetime`), under audit budget. The "no LLM" check consumes the data points emitted by `llm_sdk_denylist.py`, not the source file directly — Foundation 2's recursive constraint.

### 0.2 layer

| Signal | Fitted on (training-dataset KIND) | Verdict enum |
| --- | --- | --- |
| [signals/hook_collision.py](signals/hook_collision.py) | `hook_config` | `collides`, `clear` |
| [signals/emission_readiness.py](signals/emission_readiness.py) | `exemplar_bundle_state` | `ready`, `not_ready` |

Both signals expose `evaluate(input) -> {verdict, confidence, evidence_pointers, ...}` and ship a `PROBES` constant; `verify.py` runs the probes to confirm fit-time behavior holds at verification time.

### 0.3 layer

[orchestrate.py](orchestrate.py) — declared `DECISION_POINTS`:

```python
DECISION_POINTS = [
    ("event_validity",   "hook_event_decl"),    # 0.1 dataset membership
    ("collision_check",  "hook_collision"),     # 0.2 signal
    ("emission_gate",    "emission_readiness"), # 0.2 signal
]
```

The orchestration consults exactly these fences in this order. `verify.py` structurally checks both the order and the fence identifiers against the source.

### 0.4 layer

[verify.py](verify.py) is the grading walker. It runs steps 2–7 of [foundations/zero-four.md](../../foundations/zero-four.md)'s grading procedure: validates every collector and resolver via Foundation 2, runs every signal's probe set, validates every emitted data point against Foundation 1, structurally inspects orchestration source for declared decision-point coverage, and (when given an output bundle path) checks the bundle's manifest claim consistency and decision-point ordering against its log.

`verify.py` is itself structurally a 0.1 collector (with COLLECTOR_ID, KIND, INPUTS, collect, verify) so it is held to the same Foundation 2 constraints it applies to others.

## Operating loop

1. **`run`** — execute the orchestration:
   - For each collector, compute source_state, walk INPUTS, emit data points, persist to `datasets/<COLLECTOR_ID>.jsonl`.
   - For each signal, fit on its declared training-dataset.
   - For the candidate hook, pass through `DECISION_POINTS` in order; record each consultation as a structured log entry with `(verdict, confidence, evidence_pointers, branch_taken)`.
   - Emit `outputs/run-<hash>/{manifest.json, candidate.json, orchestration-log.jsonl}`.
   - If the emission_readiness verdict was `not_ready`, also write `exemplars/proposed/<run_id>.json` so a later human-in-the-loop step can promote it.
   - The manifest's `claim` is `"0.4"` iff the gate fired; otherwise `"candidate"`. Rejected candidates (unknown event, collision) are claimed `"rejected"`.

2. **`verify`** — run the grading procedure:
   - 18 baseline self-checks against the skill bundle.
   - +N additional self-checks against any specific output bundle passed as the argument.
   - Exit 0 iff every self-check passes. Note: a `not_ready` emission gate **does not fail verify** — it correctly produces a "candidate" claim, which is a legitimate output per [foundations/zero-four.md](../../foundations/zero-four.md).

## Work rules

- **Ride under, never replace.** This skill produces leashes; it does not relitigate Claude Code's existing rules. Hook proposals must conform to Claude Code's settings.json schema, not invent new shapes.
- **Source is first-class.** The corpus walked by collectors is the user's actual settings.json files, not a copy or fixture. Re-running against the same filesystem state must produce a byte-identical dataset modulo advisory `collected_at`.
- **No LLM in the bedrock.** The 0.1 layer (collectors, resolvers, validators) contains no model call. The 0.3 layer can be invoked by an LLM (Claude Code itself), but the orchestration source it executes is not generative — it consults declared fences and branches deterministically.
- **Honest verdicts only.** A first-run leash with no exemplar bundles emits a `"candidate"` claim, not `"0.4"`. Promoting that claim requires real exemplars, accumulated by the human via the promotion protocol in [collectors/exemplar_bundle_state.py](collectors/exemplar_bundle_state.py).
- **Audit budgets are load-bearing.** Collectors ≤ 80 lines of substantive code. Resolvers ≤ 60. Orchestration ≤ 150. Verify ≤ 200. The smallness is what makes a quiet rewrite visible in diff.
- **`MIN_EXEMPLARS = 3`** in [signals/emission_readiness.py](signals/emission_readiness.py) is the only authored number in the bedrock. Everything else is fitted to data. Changing it is a deliberate, file-level edit.

## Levels

- **v0.1 (current)** — manual run/verify. The skill is invoked from the command line; outputs are written to disk; promotion of exemplars is a manual file-copy step. One harness surface (`settings.json` hooks). First-run candidates only; no 0.4 emissions yet because the exemplar dataset is empty.
- **v0.2** — exemplar accretion. Once `exemplars/promoted/` has ≥ 3 entries, `emission_readiness` can fire `ready` and bundles can claim `"0.4"`. The leash is invoked across more candidate hooks; the dataset of `hook_config` data points grows as users configure more hooks; collision signals get sharper.
- **v0.3** — sibling leashes. The skeleton in this skill spawns leashes for other Claude Code harness surfaces (slash commands, MCP wirings, CLAUDE.md sections, agent definitions). Each new leash bedrock-conforming under the same rules; the foundations/ directory is shared. See [recursion-seam.md](recursion-seam.md).

## Files

- [SKILL.md](SKILL.md) — this file.
- [verify.py](verify.py) — the 0.4 grading walker.
- [orchestrate.py](orchestrate.py) — the 0.3 entry point.
- [recursion-seam.md](recursion-seam.md) — how this leash spawns siblings.
- [lib/](lib/) — Foundation 1/2/3 implementations.
- [collectors/](collectors/) — 0.1 source-walking programs.
- [resolvers/](resolvers/) — 0.1 pointer-resolution programs.
- [signals/](signals/) — 0.2 fitted-on-data-points functions.
- [references/hook-events.txt](references/hook-events.txt) — canonical hook-event taxonomy (source).
- [datasets/](datasets/) — collector outputs (regenerable; written by `run`).
- [outputs/](outputs/) — emitted bundles, one per run (regenerable).
- [exemplars/proposed/](exemplars/proposed/) — bundles awaiting human promotion.
- [exemplars/promoted/](exemplars/promoted/) — promoted exemplars; the `emission_readiness` training corpus.
