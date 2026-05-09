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

## Lifecycle states (project Status field)

The kanban has four columns. Each column maps to a label state and an actor:

| Status | Labels present | Who moves to this state | What it means |
|---|---|---|---|
| **Todo** | `symphony` | `new` (operator) | Issue authored, awaiting dispatch |
| **In Progress** | `symphony` + `symphony-doing` | `dispatch` (cc-symphony or operator) | Agent currently working |
| **In Review** | `symphony` + `symphony-done` (no `symphony-doing`) | `mark-done` (agent) | Agent finished, PR open, awaiting operator |
| **Done** | issue closed | `approve` (operator) | Operator approved, work merged |

Plus a project-level **Retry count** number field, incremented by `reject` each time the operator routes an issue back through retry.

## Subcommands

```
python -m skills.symphony new --title "<title>" --kind <debt|feature|refactor>   # body via stdin
python -m skills.symphony dispatch <issue-number>                                # operator manual dispatch (cc-symphony does this automatically when running)
python -m skills.symphony mark-done <issue-number>                               # agent-side; optional completion comment via stdin
python -m skills.symphony pr <issue-number> --title "<title>"                    # agent-side; PR body via stdin
python -m skills.symphony status
python -m skills.symphony review <issue-number>
python -m skills.symphony approve <issue-number> [--merge {squash,merge,rebase}]
python -m skills.symphony reject <issue-number> [--reason "<text>"]
python -m skills.symphony probe
```

### `new` — author and dispatch an issue

The agent reads the operator's verbal brief, drafts a structured issue body matching [issue_template.md](issue_template.md), then invokes:

```bash
python -m skills.symphony new --title "<title>" --kind <kind> < body.md
```

The skill: (1) creates the github issue via `gh issue create` with labels `symphony` + `kind:<kind>`; (2) adds the issue to the Projects board (project #1 under `bdf1992`); (3) sets the Status field to `Todo`. Returns the issue URL.

cc-symphony, when running, polls every `polling.interval_ms` (default 30s), sees the `symphony` label, adds `symphony-doing` automatically, spawns an agent in an isolated workspace clone, runs the body template against the issue.

### `dispatch <N>` — operator manual dispatch

What cc-symphony's orchestrator does automatically when running. Without cc-symphony, the agent (or operator) calls this to add `symphony-doing`, set Status=In Progress, and create local branch `issue-<N>`. Caller does the work on that branch then calls `mark-done`.

### `mark-done <N>` — agent completion

Agent-side completion call. Adds `symphony-done`, removes `symphony-doing`, sets Status=In Review, optionally posts a completion comment (read from stdin if non-empty). Per cc-symphony spec the agent does NOT close the issue — the operator decides via `approve`.

### `pr <N> --title "<title>"` — open a PR

Agent-side PR opener. Reads PR body from stdin. Branch must already be pushed to origin as `issue-<N>`. Opens the PR against `master` (override with `--base`).

### `status` — render the Projects board

Pulls `gh project item-list 1 --owner bdf1992 --format json`, groups by `Status` field, prints the kanban as four columns — Todo / In Progress / In Review / Done — with issue numbers + titles. Also probes cc-symphony at `http://127.0.0.1:8080/api/status` and prints `running={n} retrying={n} completed={n}` if reachable.

### `review <N>` — fetch issue + PR for operator review

Pulls the issue body + comments via `gh issue view`, finds any linked PR via `gh pr list --search "linked:#<N>"`, checks for the `symphony-done` label. Renders all three for the operator to read inline. The operator decides approve/reject through follow-up turn.

### `approve <N> [--merge {squash,merge,rebase}]` — close issue, mark Done, optionally merge PR

Closes the issue with `gh issue close <N> --reason completed`, sets project Status to `Done`. With `--merge` set, finds the linked open PR and merges it with the named strategy + deletes the head branch. Without `--merge`, the PR is left open for separate handling.

### `reject <N> [--reason "<text>"]` — route back through retry

Removes the `symphony-done` label, increments the project's Retry count number field, sets project Status to `In Progress`, optionally posts a rejection comment with the operator's reason. cc-symphony's reconciliation step will see `symphony-doing` still present and `symphony-done` absent and may retry the dispatch (per cc-symphony's retry policy; the `attempt` Liquid variable will be incremented in the body template).

### `probe` — check cc-symphony server uptime

Curls `http://127.0.0.1:8080/api/status`. Reports `running` (with `running_count`, `retrying_count`, `completed_count`) or `not_running`. No side effects.

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
