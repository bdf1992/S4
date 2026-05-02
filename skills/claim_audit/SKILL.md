---
name: claim-audit
description: Walk the repo's markdown corpus (**/*.md) and emit one md_link data point per inline link, each with a deterministic receipt — live, dangling_file, dangling_line, external, or anchor_unverified — computed against current source by path resolution and line-count check. Aggregates a claim_health signal (live_ratio, dangling counts by source) so the operator can see which prose has rotted against the code it points at. Section-anchor verification is punted (the load-bearing punt — emitted as `anchor_unverified` rather than guessed); reference-style links, autolinks, bare paths, and natural-language assertions are out of scope by construction. Built bottom-up under foundations/{data-point, collection-program, pointer, zero-four}.md, sibling to regime_audit.
when_to_use: When the operator wants accountability for the prose claims the repo makes about itself — markdown links into source, line-anchored references, cross-skill pointers — and wants a number back rather than a vibe. Read-only; writes a bundle to outputs/. Pair with subsequent renderer skills (e.g. claim-audit-report) to surface the dangling list as markdown.
argument-hint: "[<query.json>]"
allowed-tools: Bash, Read
---

> **About this skill** — surface: cross-repo prose-claim audit · rides under: Claude Code · category: bedrock-instrumentation · pattern: chain-disciplined-classifier.

# claim-audit

A 3.0 orchestration produced under 0.3 that walks every markdown file in the repo, extracts every inline link, computes a deterministic receipt for each, and emits aggregated stats. Sibling to [regime_audit](../regime_audit/SKILL.md) — same skeleton (collector → signal → orchestrate → verify), different question. `regime_audit` asks *what regime is each file?*; `claim_audit` asks *are the claims our prose makes still true against current source?*.

## Inputs

`$ARGUMENTS`:

- `[<query.json>]` — optional filter. Empty (`{}`) returns global stats. Filterable keys: `receipt`, `target_kind`, `source`. Example: `{"receipt": "dangling_file"}` returns every link whose target file does not exist.

## Bedrock pointers

- [foundations/data-point.md](../../foundations/data-point.md) → [lib/data_point.py](lib/data_point.py)
- [foundations/collection-program.md](../../foundations/collection-program.md) → [lib/collection_program.py](lib/collection_program.py) + [lib/audit.py](lib/audit.py)
- [foundations/pointer.md](../../foundations/pointer.md) → [lib/pointer.py](lib/pointer.py)
- [foundations/zero-four.md](../../foundations/zero-four.md) → [verify.py](verify.py) + [orchestrate.py](orchestrate.py)

## The chain, by file

### 1.0 layer (under 0.1)

| Collector | KIND emitted | Source walked |
| --- | --- | --- |
| [collectors/markdown_claims.py](collectors/markdown_claims.py) | `md_link` | `**/*.md` (excluding `outputs/`, `__pycache__/`, `.git/`, `node_modules/`, `.venv/`) |

Shared infrastructure: [lib/markdown_walk.py](lib/markdown_walk.py) (corpus walker, fence-aware link extractor, target resolver — pure 1.0, hoisted out of the collector to keep it under audit budget).

### 2.0 layer (under 0.2)

| Signal | Question answered | Training dataset |
| --- | --- | --- |
| [signals/claim_health.py](signals/claim_health.py) | What fraction of internal links resolve `live`? Which source files carry the most dangling claims? | `md_link` data points |

### 3.0 layer (under 0.3)

- [orchestrate.py](orchestrate.py) — runs the collector, fits the signal, evaluates an optional query, emits a bundle to `outputs/run-<hash>/`.
- [verify.py](verify.py) — bundle walker; emits `bundle_self_check` data points and exits 0 iff every check passes.

## Receipt rules (deterministic)

For each inline link `[text](href)` outside a fenced code block, compute:

1. **target_kind** — by `href` prefix and structure:
   - `external` — starts with `http://`, `https://`, `mailto:`, `ftp://`
   - `repo_path_line_anchored` — fragment matches `^L\d+(-L\d+)?$`
   - `repo_path_section_anchored` — has `#fragment` that is not a line anchor
   - `repo_path` — no fragment

2. **receipt** — by deterministic resolution against current source:
   - `external` → `external` (recorded; not graded as live or dangling)
   - `repo_path` → `live` if path exists relative to source-md's directory (and within REPO_ROOT); `dangling_file` otherwise
   - `repo_path_line_anchored` → `live` if file exists AND line range ≤ file's line count; `dangling_file` if file missing; `dangling_line` if range invalid
   - `repo_path_section_anchored` → `anchor_unverified` if file exists; `dangling_file` if file missing

The skill is healthy iff `live / internal ≥ 0.95` (where `internal = total - external`). Below that threshold, the verdict is `degraded` — the operator gets a list of dangling sources to inspect.

## Punts (v1, by construction)

These are documented as kind boundaries — the bedrock forbids LLM judgment in 1.0 collectors, so anything not mechanically extractable is out of scope:

- **Reference-style links** (`[text][ref]` with `[ref]: url` definitions). Not parsed.
- **Autolinks** (`<https://example.com>`). Not parsed.
- **Bare paths in prose** ("see foundations/data-point.md"). Not extracted — too easy to false-positive on natural-language path-shaped tokens.
- **Section-anchor existence** (`#some-heading`). Emitted as `anchor_unverified` rather than guessed; verifying these requires a full markdown heading-slug computation that v1 punts on.
- **Natural-language assertions** ("Move 1 done", "harness produces siblings", "foundations are immutable"). Out of scope; require LLM judgment, which is exactly what the bedrock fences against.

The fraction of internal claims sitting at `anchor_unverified` is itself a 2.0 signal — `unverified_ratio` — surfaced in stats. It names how much of the prose-claim surface is currently un-graded by construction.

## Outputs

After `python -m skills.claim_audit.orchestrate`:

```
skills/claim_audit/
  datasets/
    markdown_claims.jsonl       # one data point per inline link
    markdown_claims.source_state
  outputs/
    run-<hash>/
      manifest.json             # claim, decision_points, collector summary
      orchestration-log.jsonl   # per-decision branch_taken
      stats.json                # full claim_health stats
```

`verify.py` walks the skill itself plus an optional bundle dir and exits 0 iff every self-check passes — collector validation, determinism re-run, signal probes, dataset-schema check, orchestration decision-point structural check.

## Recursion seam

This skill is the second instance of the *bedrock-instrumentation* harness pattern (after `regime_audit`): same lib, same skeleton, different question. A future sibling — `commit_audit` (claims about git history), `dataset_audit` (claims about training data), `skill_doc_audit` (claims SKILL.md files make about their own components) — drops in by replicating the skeleton, swapping the collector's source-walk and the signal's verdict logic. The lib stays bedrock; what changes is what gets walked and what counts as live.

