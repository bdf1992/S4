---
tracker:
  kind: github
  repo_owner: bdf1992
  repo_name: S4
polling:
  interval_ms: 30000
workspace:
  root: ~/symphony_workspaces
agent:
  adapter: claude
  max_concurrent_agents: 2
claude:
  permission_mode: default
  skip_permissions: false
---

<!--
Symphony WORKFLOW.md for bdf1992/S4.

Front-matter is chain-validated by skills/leash_for_symphony/ — fields conform
to the closed taxonomy at skills/leash_for_symphony/references/symphony-workflow-fields.txt;
posture matches default Claude Code permissions (no skip, default mode).

Body (below this comment) is operator-authored Symphony workflow instructions
for issues in bdf1992/S4 — fill in when wiring Symphony to actually run.
-->
