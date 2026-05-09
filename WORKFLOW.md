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

## Completion protocol

When your work is complete and the PR is open:

1. Add the `symphony-done` label:
   ```
   gh issue edit {{ issue.identifier }} --repo {{ repo }} --add-label symphony-done
   ```
2. **Do NOT close the issue** — the operator reviews via `python -m skills.symphony review {{ issue.identifier }}` and closes via `python -m skills.symphony approve {{ issue.identifier }}`.
3. Post a brief completion comment on the issue summarizing: branch, PR URL, verifier status. cc-symphony's reconciliation will then remove `symphony-doing`.

{% if attempt %}

## Retry context

This is retry attempt {{ attempt }}. Re-read the prior comments on this issue to understand what failed previously before iterating. Do not duplicate the rejected work; address the rejection feedback.

{% endif %}
