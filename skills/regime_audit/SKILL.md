---
name: regime-audit
description: Walk the repo's source corpus (skills/**/*.py and **/*.md), classify each artifact by regime label (bedrock / 0.0 / 0.1 / 0.2 / 0.3 / unclassified — the code-emitted protocol-tagged strings) using observable AST signals (top-level constants, import roots, file location), and emit aggregated stats — counts by regime, kind, and skill, plus a floor_ratio (0.1+0.2)/0.3 that names the success metric from CLAUDE.md. Fuzzy cases are emitted as `unclassified` rather than guessed; the rule table is procedural, not generative. Built bottom-up under foundations/{data-point, collection-program, pointer, zero-four}.md, sibling to leash_for_hooks.
when_to_use: When the operator wants a snapshot of where the chain stands — how thick the 1.0+2.0 substrate (the code-emitted "0.1" + "0.2" labels) is relative to 3.0 free-write ("0.3" label), which skills are mature vs early, what falls outside the bedrock pattern. Read-only; writes a bundle to outputs/. Pair with regime-audit-report to render the bundle as markdown.
argument-hint: "[<query.json>]"
allowed-tools: Bash, Read
---

> **About this skill** — surface: cross-skill repo audit · rides under: Claude Code · category: bedrock-instrumentation · pattern: chain-disciplined-classifier.

# regime-audit

A 3.0 orchestration produced under 0.3 that walks the repo, classifies every Python and Markdown artifact by regime, and emits aggregated stats. Companion to [regime_audit_report](../regime_audit_report/render.py) which renders the bundle as a markdown report.

## Inputs

`$ARGUMENTS`:

- `[<query.json>]` — optional filter. Empty (`{}`) returns global stats. Filterable keys: `regime`, `kind`, `skill`. Example: `{"regime": "0.2"}` returns the 2.0 signal files (regime values are stored as the code-emitted labels `"0.1"` / `"0.2"` / `"0.3"`, which tag each artifact with the protocol that produced it).

## Bedrock pointers

- [foundations/data-point.md](../../foundations/data-point.md) → [lib/data_point.py](lib/data_point.py)
- [foundations/collection-program.md](../../foundations/collection-program.md) → [lib/collection_program.py](lib/collection_program.py) + [lib/audit.py](lib/audit.py)
- [foundations/pointer.md](../../foundations/pointer.md) → [lib/pointer.py](lib/pointer.py)
- [foundations/zero-four.md](../../foundations/zero-four.md) → [verify.py](verify.py) + [orchestrate.py](orchestrate.py)

## The chain, by file

### 1.0 layer (under 0.1)

| Collector | KIND emitted | Source walked |
| --- | --- | --- |
| [collectors/regime_classification.py](collectors/regime_classification.py) | `regime_classification` | `skills/**/*.py`, `**/*.md`, `foundations/llm-sdk-denylist.txt` |

Shared infrastructure: [lib/source_features.py](lib/source_features.py) (AST helpers, denylist read, target walker — pure 1.0, hoisted out of the collector to keep it under audit budget).

### 2.0 layer (under 0.2)

| Signal | Question answered | Training dataset |
| --- | --- | --- |
| [signals/regime_distribution.py](signals/regime_distribution.py) | What's the regime distribution? Is the 1.0+2.0 floor growing relative to 3.0? | `regime_classification` data points |

### 3.0 layer (under 0.3)

- [orchestrate.py](orchestrate.py) — runs the collector, fits the signal, evaluates an optional query, emits a bundle to `outputs/run-<hash>/`.
- [verify.py](verify.py) — bundle walker; emits `bundle_self_check` data points and exits 0 iff all checks pass.

## Classification rules (priority order)

Python files (first match wins):

1. `imports_llm_sdk` (any import root in the denylist) → `0.3` / `llm_using`
2. `is_orchestrate` (filename = `orchestrate.py`) → `0.3` / `orchestration`
3. `is_verify` (filename = `verify.py`) → `0.3` / `verification`
4. `is_render` (filename = `render.py`) → `0.1` / `renderer`
5. `has_SIGNAL_ID` (top-level constant) → `0.2` / `signal`
6. `has_RESOLVER_ID` (top-level constant) → `0.1` / `resolver`
7. `has_COLLECTOR_ID` OR `calls_make_data_point` → `0.1` / `collector`
8. `in_lib_dir` (path component is `lib`) → `0.1` / `infrastructure`
9. `in_scripts_dir` (path component is `scripts`) → `0.1` / `script`
10. filename = `__init__.py` → `0.1` / `package_marker`
11. otherwise → `unclassified` / `unknown_python`

Markdown files:

1. path starts with `foundations/` → `bedrock` / `foundation_spec`
2. filename = `CLAUDE.md` → `0.0` / `harness_root`
3. filename = `SKILL.md` → `0.0` / `skill_doc`
4. path starts with `meeting-notes/` or `debts/` → `0.0` / `operator_note`
5. path contains `skills/` → `0.0` / `skill_doc`
6. otherwise → `0.0` / `prose`

All signals are observable from AST or path. No prose vibes.
