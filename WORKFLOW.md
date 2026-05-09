---
tracker:
  kind: github
  repo: "bdf1992/S4"
  api_key: "$GITHUB_TOKEN"
  labels: ["symphony"]

polling:
  interval_ms: 30000

agent:
  max_concurrent_agents: 2

claude:
  model: "claude-sonnet-4-6"
  skip_permissions: false
  allowed_tools:
    - "Bash"
    - "Read"
    - "Write"
    - "Edit"
    - "Grep"
    - "Glob"

workspace:
  root: "~/symphony-workspaces"
---

You are a coding agent working under the franchise kit at {{ repo }}.

## Issue
**#{{ issue.identifier }} — {{ issue.title }}**

{{ issue.description }}

## Your kit (read these first)

- [CLAUDE.md]({{ repo }}/blob/master/CLAUDE.md) — load-bearing rules, vocabulary, anti-patterns. Read at session start.
- [foundations/]({{ repo }}/tree/master/foundations) — bedrock specs (data-point, collection-program, pointer, zero-four). Immutable.
- [skills/]({{ repo }}/tree/master/skills) — pre-existing skills you ride under. Use what's there before authoring new.
- [debts/]({{ repo }}/tree/master/debts) — tracked open gaps. If your issue references `D-NNN`, the debt record specifies the payoff. Schema: [debts/schema.md]({{ repo }}/blob/master/debts/schema.md).
- [boards/schema.md]({{ repo }}/blob/master/boards/schema.md) — kanban geometry for any board work.
- [paradigm/README.md]({{ repo }}/blob/master/paradigm/README.md) — active spike state; check before continuing paradigm work.

## How to work this issue

1. **Branch:** you are on `issue-{{ issue.identifier }}` already (cc-symphony provisioned it).
2. **Read the issue body** — success criteria, out-of-scope fences, depends-on, blast-radius. The body is your contract; do not free-write past it.
3. **Do the work** — prefer editing existing files; no co-authored-by trailer in commits; one focused commit per slice.
4. **Verify:** run `python -m skills.leash_for_hooks.verify` (must stay 19/19 green). Run any verifier specific to your slice.
5. **Commit** with `Refs #{{ issue.identifier }}` trailer in the message.
6. **Push:** `git push -u origin issue-{{ issue.identifier }}`.
7. **Open a PR:** `gh pr create --repo {{ repo }} --base master --head issue-{{ issue.identifier }} --title "<concise title>" --body "<summary referencing the issue + verifier output>"`.

## Completion protocol — produce an acceptance walkthrough

The operator's review surface is **the acceptance walkthrough**, not the diff or the commit journey. Their job is to confirm the outcome, not to audit how you got there. So your completion is *not* a step-by-step report — it's a demonstration of the outcome.

When your work is complete and the PR is open:

1. **Post the acceptance walkthrough as a comment on the issue.** It must demonstrate the outcome named in the issue's success criteria:
   - Verifier output verbatim (e.g., `python -m skills.leash_for_hooks.verify` → `19 self-checks, 0 failures`)
   - Before/after of measurable state for any behavior change (e.g., `radon cc` output before vs. after for a complexity refactor)
   - Each success criterion checked against ground truth — show *the criterion* and *the evidence it holds*, one per line
   - Pointers (file:line) to the artifacts that changed, for the operator to spot-check if they want — but the walkthrough must stand on its own without requiring them to crawl the diff

   Do not narrate steps. Do not list what you did. The operator should be able to read this comment and decide approve/reject without opening a single file.

2. Add the `symphony-done` label:
   ```
   gh issue edit {{ issue.identifier }} --repo {{ repo }} --add-label symphony-done
   ```
3. **Do NOT close the issue** — the operator reviews via `python -m skills.symphony review {{ issue.identifier }}` and approves via `python -m skills.symphony approve {{ issue.identifier }} --merge squash`. cc-symphony's reconciliation will then remove `symphony-doing`.

{% if attempt %}

## Retry context

This is retry attempt {{ attempt }}. Re-read the prior comments on this issue to understand what failed previously before iterating. Do not duplicate the rejected work; address the rejection feedback.

{% endif %}
