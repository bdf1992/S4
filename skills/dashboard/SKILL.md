---
name: dashboard
description: Four views over the same live source — markdown render (at-a-glance tables), snapshot capture (persisted observation of state-at-time), narrate (delta-aware prose vs last snapshot), and html (self-contained browser-viewable page with sparkline). Composes every existing artifact in the repo — bedrock primitives, board health, floor-ratio with trend, leash registry, per-skill regime distribution. Pure 1.0 deterministic; no LLM in the renders. Snapshots persist as derived observations under outputs/run-<sha8>/, deduplicated by content hash.
when_to_use: When the operator wants to look at where the experiment stands. Use `render` for at-a-glance markdown tables in the terminal, `narrate` for prose with deltas since last snapshot ("the floor moved, debt D-005 closed, leash toggle flipped"), `html` for a polished browser-viewable page (good for sharing or visual scanning with a sparkline trend), `snapshot` to mark a baseline without rendering. Pairs with per-board kanbans (`python -m boards <name>`) and regime-audit-report (one audit bundle in detail).
argument-hint: "render | snapshot | narrate | html"
allowed-tools: Bash, Read
---

> **About this skill** — surface: cross-artifact operator dashboard · rides under: Claude Code · category: artifact-view · pattern: artifact-skill-split (memory: view-shaped requests default to artifact + render-skill).

# dashboard

A 1.0 deterministic render (produced under 0.1) that composes the existing artifact substrate into one operator-facing markdown document. No new artifact, no new collector — the dashboard is a *view* over what already lives on disk.

## Four entry points

```
python -m skills.dashboard.render             # markdown tables, at-a-glance (no persistence)
python -m skills.dashboard.render --no-trend
python -m skills.dashboard.snapshot            # capture and persist current state to outputs/
python -m skills.dashboard.snapshot --print   # capture and print the snapshot dict (no write)
python -m skills.dashboard.narrate             # prose narrative; compares live state to last snapshot; persists new snapshot at end
python -m skills.dashboard.narrate --no-save   # narrate without persisting (one-off look)
python -m skills.dashboard.html                # self-contained HTML to stdout (pipe to a file)
python -m skills.dashboard.html -o page.html   # self-contained HTML written to file
```

`render`, `narrate`, and `html` print to stdout by default. `narrate` writes the new snapshot at the end (unless `--no-save`); confirmation goes to stderr. The HTML page uses `vscode://file/` URIs for source links — click jumps to the file in VSCode if the protocol handler is registered.

## What it surfaces

1. **Bedrock primitives** — the five immutable foundation specs. Existence + last-modified date computed live from the filesystem.
2. **Floor ratio** — latest value from the most recent `skills/regime_audit/outputs/run-*/` bundle, plus a one-line trend across all bundles in chronological order.
3. **Boards** — one row per sub-board (debts, grading-events, exemplars), delegating to [boards/adapters/all_boards.py](../../boards/adapters/all_boards.py). Health rolls up to needs_attention vs healthy.
4. **Leashes** — one row per `skills/leash_*/`, pulling toggle state from each `leash_state.json`.
5. **Skills regime distribution** — per-skill counts by regime label (0.0 / 0.1 / 0.2 / 0.3 / unclassified — code-emitted protocol-tagged strings from the regime_audit collector), pulled from the latest audit bundle's `stats.json`.

Each number is followed by a markdown link to its source — bedrock pointer discipline (`foundations/pointer.md`).

## Why one collector and two renders

The underlying substrate (debts, grading events, leash states, audit bundles, foundation specs) is already on disk and walked live by every render. What `snapshot` adds is one extra artifact — `outputs/run-<sha8>/snapshot.json` — that captures the *aggregated state* at a moment in time so `narrate` can emit deltas. The snapshot is a derived observation, not source: regenerable from the same working-tree state (content-hashed, deduplicated), and never authoritative. Same pattern as `skills/regime_audit/outputs/run-*/stats.json` — historical observations make trend-talk possible.

Per CLAUDE.md *Sub to source*: derived snapshots are regenerable, not persisted as authoritative source. The snapshots here are persisted *as observations*, not as source replicas — the source files (debts/, foundations/, leash states) remain canonical.

Per the artifact-skill split (memory: view-shaped requests default to artifact + render-skill, never fused): the snapshot is the artifact (agent-native, JSON, schema-shaped); `render` and `narrate` are two render-skills that surface it differently. Adding a third render (HTML, terminal-pretty, etc.) does not require touching the snapshot.

## Pairs with

- [boards/](../../boards/) — per-source kanban views; the dashboard summarizes their health, the kanbans expand each one.
- [skills/regime_audit/](../regime_audit/) — emits the bundles this dashboard's floor-ratio section reads.
- [skills/regime_audit_report/](../regime_audit_report/) — renders one audit bundle in full table form; the dashboard surfaces only the headline number plus trend.
