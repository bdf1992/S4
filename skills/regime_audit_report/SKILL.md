---
name: regime-audit-report
description: Render a regime_audit bundle's stats.json into a human-viewable markdown report with tables for regime, kind, skill, and (when filtered) matching paths. Pure 1.0 deterministic transform — same input produces byte-identical output. Decoupled from regime_audit so the artifact format and the view format can evolve independently.
when_to_use: When the operator wants to read the audit results as a formatted document instead of CLI output. Pairs with regime-audit (which produces the stats.json artifact this skill consumes).
argument-hint: "<bundle-dir|--latest>"
allowed-tools: Bash, Read
---

> **About this skill** — surface: render-skill for regime_audit bundles · rides under: Claude Code · category: artifact-view · pattern: artifact-skill-split (memory: view-shaped requests default to artifact + render-skill).

# regime-audit-report

A 1.0 deterministic render (under 0.1): `stats.json` → `report.md`. No LLM, no nondeterminism. Lives in its own skill folder so the renderer's evolution doesn't churn the audit's artifact contract.

## Inputs

`$ARGUMENTS`:

- `<bundle-dir>` — path to a `skills/regime_audit/outputs/run-<hash>/` directory.
- `--latest` — render the most recently emitted bundle.

Writes `report.md` adjacent to the input `stats.json`.

## Why a separate skill

The audit produces a structured artifact (`stats.json`); the report is one possible view. Keeping them separate means:

- the artifact contract is stable even if the report layout evolves,
- different render-skills (e.g. HTML, terminal-pretty) can attach to the same artifact without touching the audit pipeline,
- the audit's bundle stays minimal — render output is opt-in.
