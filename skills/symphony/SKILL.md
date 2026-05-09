---
name: symphony
description: Operator-facing lifecycle skill for cc-symphony work on bdf1992/S4. Wraps `gh` CLI + cc-symphony's HTTP server so the operator's entire interaction with github issues, the Projects board, agent-completion review, and approve/reject decisions stays verbal-with-the-agent rather than click-driven. Subcommands — `new` to author and dispatch a labeled issue with structured body (the agent drafts the body, the skill writes it to github + adds to project + sets initial Status); `status` to render the Projects board state as text; `review <N>` to fetch issue + PR + symphony-done state for operator review; `approve <N>` to close the issue and move it to Done; `reject <N>` to remove `symphony-done` and route back to In Progress for retry; `probe` to check whether cc-symphony's HTTP server is running locally on port 8080. Distinct from leash_for_symphony — that skill grades the WORKFLOW.md config; this one drives the github lifecycle the config orchestrates.
when_to_use: When the operator names work that should flow through cc-symphony rather than direct execution. Triggers — "open an issue about X", "review issue N", "approve issue N", "reject N", "what's the symphony state", "is symphony running". Default for any work the operator wants tracked, parallelizable, or auditable through the issue lifecycle.
argument-hint: "[new|status|review|approve|reject|probe] [<title>|<issue-number>]"
allowed-tools: Bash, Read
---

> **About this skill** — surface: github + cc-symphony lifecycle · rides under: Claude Code · category: operator-interface · pattern: dev-execution-not-click-execution. License: MIT.

# symphony

Operator interface for the cc-symphony work lifecycle on `bdf1992/S4`. Every step the operator would otherwise click through (open issue, label, add to project, set status, review, approve, close) is a verbal directive routed through this skill.

This is a **3.0 program under 0.3 discipline** — the agent (me) does judgment work (drafting issue bodies from operator briefs, surfacing review context, deciding approve-vs-reject framing); the skill does deterministic work (gh CLI calls, JSON parsing, status writes). The seam between LLM-judgment and deterministic-execution is the line between this `SKILL.md` (which I read at invocation time to know how to draft) and `lifecycle.py` (which is pure 1.0 — no LLM, just gh CLI).

## Subcommands

```
python -m skills.symphony new --title "<title>" --kind <debt|feature|refactor>     # body via stdin
python -m skills.symphony status
python -m skills.symphony review <issue-number>
python -m skills.symphony approve <issue-number>
python -m skills.symphony reject <issue-number>
python -m skills.symphony probe
```

### `new` — author and dispatch an issue

The agent reads the operator's verbal brief, drafts a structured issue body matching [issue_template.md](issue_template.md), then invokes:

```bash
python -m skills.symphony new --title "<title>" --kind <kind> < body.md
```

The skill: (1) creates the github issue via `gh issue create` with labels `symphony` + `kind:<kind>`; (2) adds the issue to the Projects board (project #1 under `bdf1992`); (3) sets the Status field to `Todo`. Returns the issue URL.

cc-symphony, when running, polls every `polling.interval_ms` (default 30s), sees the `symphony` label, adds `symphony-doing` automatically, spawns an agent in an isolated workspace clone, runs the body template against the issue.

### `status` — render the Projects board

Pulls `gh project item-list 1 --owner bdf1992 --format json`, groups by `Status` field, prints a kanban-shaped text rendering — Todo / In Progress / Done columns with issue numbers + titles + labels. Also probes cc-symphony at `http://127.0.0.1:8080/api/status` (silently — adds a status line if the server is running, omits if not).

### `review <N>` — fetch issue + PR for operator review

Pulls the issue body + comments via `gh issue view`, finds any linked PR via `gh pr list --search "linked:#<N>"`, checks for the `symphony-done` label. Renders all three for the operator to read inline. The operator decides approve/reject through follow-up turn.

### `approve <N>` — close issue, mark Done

Closes the issue with `gh issue close <N> --reason completed`, sets project Status to `Done`, leaves all labels. The completed work is now part of github's permanent issue history; the agent's PR (if any) lands separately on its own approval cycle.

### `reject <N>` — remove `symphony-done`, route to retry

Removes the `symphony-done` label via `gh issue edit <N> --remove-label symphony-done`, sets project Status to `In Progress`, optionally adds a comment with the operator's rejection reason. cc-symphony's reconciliation step will see `symphony-doing` still present and `symphony-done` absent and may retry the dispatch (depends on retry-policy in WORKFLOW.md).

### `probe` — check cc-symphony server uptime

Curls `http://127.0.0.1:8080/api/status`. Reports `running` (with active-run count, completed-count) or `not_running`. No side effects.

## Issue body template

The agent fills [issue_template.md](issue_template.md) before invoking `new`. Template structure:

- **Brief** — operator's intent, restated by the agent in 1–2 sentences (verifies intent before writing to github).
- **Success criteria** — checkable bullets the agent (or human) can verify when the work is complete.
- **Out of scope** — explicit fences against scope creep.
- **Depends on** — issue / debt / file references that gate this work.
- **Blast radius** — `low | medium | high` + one-line description.

The agent's drafting work is judgment — what counts as a success criterion, what the blast radius is, what's in vs out of scope. The template just gives the deterministic structure.

## Pairs with

- [skills/leash_for_symphony/](../leash_for_symphony/) — grades the WORKFLOW.md config; this skill drives the work the config orchestrates. They are independent — this skill works without leash_for_symphony, and leash_for_symphony is a static-analysis surface that doesn't dispatch.
- [skills/dashboard/](../dashboard/) — when extended (per the issue at `#5` once created), would surface symphony-state alongside debts/leashes/regime-audit. Until then, `symphony status` is the read surface.
- cc-symphony binary (not installed yet) — when running, picks up symphony-labeled issues and dispatches agents. This skill is functional without cc-symphony (manual lifecycle) but auto-coordinates when cc-symphony is up.

## What this skill does NOT do

- It does not install or run cc-symphony — that's a separate operator concern (clone, build, run with WORKFLOW.md path).
- It does not author the WORKFLOW.md body template — that's tracked as issue `#5` in S4.
- It does not review the agent's actual code — `review <N>` surfaces context for the operator to read; only the operator decides approve/reject.
- It does not bypass `skip_permissions: false` — spawned agents under cc-symphony still pause for tool prompts unless the operator flips that posture in WORKFLOW.md.
