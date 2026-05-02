# Books-close digest — 2026-05-01

**Author:** agent (Claude Opus 4.7) at operator's directive *"I need it now for a clean/booking loop."*
**Status:** decision surface. Nothing is committed by writing this. Operator points at groups; agent stages and commits each in sequence.
**Source state at write time:** `git:b7aa043` (HEAD).
**Backlog:** 39 modified + 31 untracked = **70 entries**.

## How to use

Each numbered group below is a **candidate commit**. For each: stakes (one line), files in scope, proposed commit message header. Scan top to bottom. At the end, name the groups you want committed (e.g., *"do A1, A2, B1–B4, D, then stop"*) and the agent stages and commits in sequence. You can override any commit message at stage time. Nothing autonomous past your green light.

Two flagged items at the bottom are **decisions, not commits** — orphans / questionable groupings the operator should call before they get committed under any group.

---

## Wave A — Vocabulary lift (Events 002 + 003)

`foundations/grading-events.md` records two IN-PROGRESS events at 2026-05-01: **Event 002** (programs vs protocols two-axis lift across foundations and downstream skills, renaming-only, shapes preserved) and **Event 003** (validation-scope rule — lower-layer validators don't block, blocking moves to 0.3/3.0 and 0.4/4.0 produced artifacts). Both were applied by direct operator authorization; both are awaiting commit SHAs in their resolution lines. Wave A is the work that closes those events.

**Commit order matters:** A1 → A2 → A3..A8 (any order) → A9 last (Event log fills in SHAs).

### A1 — CLAUDE.md (originator of Events 002 + 003)

**Stakes:** project-instructions update; both grading events cite this file as the trigger document. Without this commit, the foundations and downstream skills look like silent revision.
**Files (1):** `CLAUDE.md` (141 lines).
**Proposed message:** `CLAUDE.md: two-axis programs/protocols framing + validation-scope rule (Events 002 + 003)`

### A2 — foundations/ vocabulary lift

**Stakes:** the bedrock-immutability rule says these only change via a graded event; Event 002 is that event. Renaming-only; substantive shapes (data-point fields, collector constraints, pointer protocol, 4.0 composition rule, proposal contract) are preserved per the event's investigation block.
**Files (5):** `foundations/data-point.md` (16), `foundations/collection-program.md` (18), `foundations/pointer.md` (26), `foundations/proposal.md` (50), `foundations/zero-four.md` (152). zero-four.md also carries Event 003's validation-scope edits — folded in.
**Proposed message:** `foundations: vocabulary lift to two-axis (X.0 programs / 0.X protocols) + validation-scope rule (Events 002 + 003)`

### A3 — leash_for_hooks vocabulary lift

**Stakes:** existing skill caught up with the new vocabulary; SKILL.md description and "ladder by file" → "chain by file" headings updated; verify.py and lib/leash_state.py touched along the way.
**Files (5):** `skills/leash_for_hooks/SKILL.md` (52), `skills/leash_for_hooks/orchestrate.py` (3), `skills/leash_for_hooks/verify.py` (47), `skills/leash_for_hooks/lib/leash_state.py` (16), `skills/leash_for_hooks/recursion-seam.md` (28).
**Note (A3.1):** `skills/leash_for_hooks/lib/receipts.py` is **new (untracked)** — likely lib infrastructure added during the lift. Recommend folding into A3 unless its addition was independent. *See flagged item F1.*
**Proposed message:** `leash_for_hooks: vocabulary lift to chain/X.0/0.X (Event 002)`

### A4 — leash_for_slash_commands vocabulary lift

**Stakes:** sibling skill, same lift as A3.
**Files (3):** `skills/leash_for_slash_commands/SKILL.md` (40), `skills/leash_for_slash_commands/orchestrate.py` (3), `skills/leash_for_slash_commands/verify.py` (35).
**Proposed message:** `leash_for_slash_commands: vocabulary lift to chain/X.0/0.X (Event 002)`

### A5 — orchestration_audit vocabulary lift

**Stakes:** "0.3 self-report" → "3.0 self-report"; "0.2 model fit" → "2.0 model fit (under 0.2)" — same lift pattern. Recently committed work (b7aa043 et al.) gets the rename pass.
**Files (3):** `skills/orchestration_audit/SKILL.md` (12), `skills/orchestration_audit/0_2_design.md` (18), `skills/orchestration_audit/verify.py` (32).
**Proposed message:** `orchestration_audit: vocabulary lift to chain/X.0/0.X (Event 002)`

### A6 — claim_audit vocabulary lift

**Stakes:** small lift; verify.py update may be more than rename — agent has not deeply read it. Check at stage time.
**Files (2):** `skills/claim_audit/SKILL.md` (19), `skills/claim_audit/verify.py` (9).
**Note:** `skills/claim_audit/datasets/` and `skills/claim_audit/outputs/` are **new (untracked)** — runtime output. *See flagged item F4.*
**Proposed message:** `claim_audit: vocabulary lift to chain/X.0/0.X (Event 002)`

### A7 — tools/ vocabulary lift in renderers

**Stakes:** render labels (REVIEW page text) and section headings updated to two-axis vocabulary.
**Files (2):** `tools/render_proposals.py` (91), `tools/render_proposals_html.py` (157).
**Note:** the corresponding render outputs `proposals/REVIEW.md` (78) and `proposals/REVIEW.html` (81) re-emit from these. Bundle them with A7 unless the operator wants render outputs as their own commit. *See flagged item F5.*
**Proposed message:** `tools/render_proposals: vocabulary lift in render output labels (Event 002)`

### A8 — README.md vocabulary lift

**Stakes:** project README updated to two-axis vocabulary.
**Files (1):** `README.md` (48).
**Proposed message:** `README: two-axis programs/protocols framing (Event 002)`

### A9 — grading-events.md catch-up (LAST commit of Wave A)

**Stakes:** records SHAs from A1–A8 into the resolution lines of Events 002 + 003. Closes the IN-PROGRESS state. Without this commit, the events stay marked unresolved in perpetuity.
**Files (1):** `foundations/grading-events.md` (53 new lines).
**Proposed message:** `foundations/grading-events: log Events 002 + 003 with commit SHAs`
**Note:** Agent will collect SHAs from A1–A8 at commit time and substitute them into the file before staging A9.

---

## Wave B — New skills (untracked)

Each is its own commit; ordering doesn't matter relative to Wave A.

### B1 — skills/leash_for_symphony/

**Stakes:** new harness skill — mirrors `proposals/prop_2026-04-30_leash-for-symphony/` (Wave C2). Ships the candidate as the actual skill folder. Sibling to leash_for_hooks and leash_for_slash_commands.
**Files:** entire `skills/leash_for_symphony/` directory (SKILL.md, orchestrate.py, verify.py, collectors/, datasets/, exemplars/, references/, signals/, leash_state.json, outputs/). Excludes `__pycache__`.
**Proposed message:** `leash_for_symphony: new harness skill — sibling to leash_for_hooks/leash_for_slash_commands`

### B2 — skills/regime_audit/

**Stakes:** new skill — purpose to be confirmed by operator; agent has not read its SKILL.md.
**Files:** entire `skills/regime_audit/` directory (SKILL.md, orchestrate.py, verify.py, collectors/, datasets/, signals/, lib/, example-query.json, outputs/). Excludes `__pycache__`.
**Proposed message:** `regime_audit: new skill` *(operator: confirm purpose line at stage time)*

### B3 — skills/regime_audit_report/

**Stakes:** new render-skill paired with B2. Per the artifact-render split convention from prior course-corrections, this is the renderer for regime_audit's output.
**Files:** entire `skills/regime_audit_report/` directory (SKILL.md, render.py). Excludes `__pycache__`.
**Proposed message:** `regime_audit_report: render skill for regime_audit output`

### B4 — skills/dashboard/

**Stakes:** new render-skill (`html.py`, `narrate.py`, `render.py`, `snapshot.py`). Likely the dashboard side of `prop_2026-04-30_verifier-for-dashboard`.
**Files:** entire `skills/dashboard/` directory. Excludes `__pycache__`.
**Proposed message:** `dashboard: new render skill`

---

## Wave C — New proposals (untracked)

Each is its own commit. Self-contained directories (proposal.json + README.md + candidate/ + gap.json + pre_verification.json).

### C1 — prop_2026-04-30_leash-for-cc-afk/

**Proposed message:** `proposals: leash-for-cc-afk — new proposal directory`

### C2 — prop_2026-04-30_leash-for-symphony/

**Stakes:** the proposal that B1 graduates from. Conventionally both ship together; commit C2 before B1 if you want the proposal-then-skill audit trail to be clean. *See flagged item F2.*
**Proposed message:** `proposals: leash-for-symphony — new proposal directory`

### C3 — prop_2026-05-01_mutation-operator-catalog/

**Proposed message:** `proposals: mutation-operator-catalog — new proposal directory`

### C4 — prop_2026-05-01_surface-inventory-and-expectation-check/

**Stakes:** referenced in [skills/gap_audit/datasets/2026-05-01/surface_inventory_absence.jsonl](../skills/gap_audit/datasets/2026-05-01/surface_inventory_absence.jsonl) as the proposal closing 24 gap data points. Bundles its own gap collector, candidate, pre-verification.
**Proposed message:** `proposals: surface-inventory-and-expectation-check — new proposal directory`

---

## Wave D — Modified proposal artifacts

Existing proposal directories with edits — likely Event 002 vocabulary lift in their READMEs and `expected_behavior.md` files.

### D1 — Modified proposals (one commit, the wave-style)

**Stakes:** lift the existing proposal text to the new vocabulary alongside Wave A.
**Files (5):** `proposals/prop_2026-04-30_parameterized-bundle-verifier/README.md` (8), `proposals/prop_2026-04-30_verifier-for-dashboard/{candidate/sample/expected_behavior.md (2), proposal.json (27)}`, `proposals/prop_2026-04-30_verifier-for-orchestration-audit/candidate/sample/expected_behavior.md` (4), `proposals/prop_2026-04-30_verifier-for-regime-audit-report/{candidate/sample/expected_behavior.md (2), proposal.json (25)}`.
**Note:** proposal.json modifications are 27 + 25 lines — that's structural change, not just text. Agent has not read the diffs. Operator should spot-check at stage time. *See flagged item F3.*
**Proposed message:** `proposals: vocabulary lift across existing proposal artifacts (Event 002)` — pending content verification.

---

## Wave E — Boards system overhaul

`boards/__main__.py` heavily modified (191 lines) plus a full new layer: `collectors/`, `datasets/`, `lib/`, plus `boards/render_html.py` (new) and `boards/adapters/factory_opportunities.py` (new). `boards/adapters/all_boards.py` modified (6 lines).

### E1 — boards system

**Stakes:** coherent rewrite of the boards system. New collector pattern (mirrors gap_audit's collector pattern), new dataset emission, new render path. Likely the operator-driven decision-surface infrastructure pattern.
**Files:** all `boards/` modifications + entire untracked `boards/{collectors,datasets,lib,render_html.py,adapters/factory_opportunities.py}`. Excludes `__pycache__`.
**Note:** boards/datasets/*.{jsonl,source_state} are **emitted artifacts**, not source. Convention from skills/gap_audit suggests these *do* get committed (for grading reproducibility). Confirm.
**Proposed message:** `boards: collector-based architecture with cards datasets + html renderer`

---

## Wave F — Gap collector additions

### F1 — New gap collectors + their datasets

**Files:** `skills/gap_audit/collectors/{surface_handwalk_recurrence.py, surface_inventory_absence.py, verifier_redundancy.py}` + `skills/gap_audit/datasets/2026-04-30/{surface_handwalk_recurrence.{jsonl,source_state}, verifier_redundancy.{jsonl,source_state}}` + `skills/gap_audit/datasets/2026-05-01/` + `skills/gap_audit/signals/` + `skills/gap_audit/references/`.
**Proposed message:** `gap_audit: three new collectors + datasets (surface_handwalk_recurrence, surface_inventory_absence, verifier_redundancy)`

### F2 — gap_audit dataset re-emissions (modified)

**Stakes:** existing datasets re-emitted at a newer source_state (auto-regen, not human-authored).
**Files (4):** `skills/gap_audit/datasets/2026-04-30/{collector_with_dangling_inputs,skill_without_verifier}.{jsonl,source_state}`.
**Proposed message:** `gap_audit: refresh dataset emissions for collector_with_dangling_inputs + skill_without_verifier`
**Recommend:** fold into F1 unless audit-trail wants them separate.

---

## Wave G — Tools (new, separate from A7's modifications)

### G1 — tools/monitor.py + tools/shim_coverage.py

**Stakes:** two new tools. Agent has not read them; purpose to be confirmed.
**Files (2):** `tools/monitor.py`, `tools/shim_coverage.py`.
**Proposed message:** `tools: monitor + shim_coverage` *(operator: confirm purpose line)*

---

## Wave H — Meeting-notes (untracked)

### H1 — meeting-notes index + 2026-04-29 notes

**Files (3):** `meeting-notes/2026-04-29-continuous-process-framing.md`, `meeting-notes/2026-04-29-receipts-and-existing-structure.md`, `meeting-notes/meeting-schedule.md`.
**Proposed message:** `meeting-notes: 2026-04-29 alignment threads + scheduling pattern`

### H2 — meeting-notes 2026-05-01 heartbeat-frame

**Stakes:** the meeting note from this session capturing the heartbeat reframe.
**Files (1):** `meeting-notes/2026-05-01-heartbeat-frame.md`.
**Proposed message:** `meeting-notes: 2026-05-01 heartbeat frame for time-surface harness (T6)`

---

## Wave I — Operator infrastructure (untracked)

### I1 — .claude/

**Stakes:** project-local Claude Code settings/agents/skills directory. Whether to commit depends on whether the operator wants per-project harness state in version control. *See flagged item F6.*
**Files:** entire `.claude/` directory.
**Proposed message:** `.claude: project-local harness configuration` *(or — commit deferred per F6)*

### I2 — approvals/

**Stakes:** new approval-ledger surface. Contains `decisions.jsonl`. Per the franchise-books framing, this IS load-bearing record state and belongs in version control.
**Files:** `approvals/decisions.jsonl` and the now-being-written `approvals/books_close_2026-05-01.md` (this file).
**Proposed message:** `approvals: ledger surface + first books-close digest`

### I3 — overnight_log.jsonl

**Stakes:** 14-line log from a recent overnight run. Whether to commit depends on whether overnight logs are version-controlled records or per-session artifacts. *See flagged item F7.*
**Files (1):** `overnight_log.jsonl`.
**Proposed message:** `overnight: 2026-05-01 run log` *(or — gitignore per F7)*

---

## Flagged items — decisions, not commits

These need an operator call before they get folded into any group above.

### F1 — `skills/leash_for_hooks/lib/receipts.py` (untracked)

New file inside an existing skill that has tracked modifications (Wave A3). Agent does not know whether this was added as part of the vocabulary lift or as separate infrastructure. Two options:
- **Fold into A3** — same skill, same wave, same review surface.
- **Separate commit** — receipts.py is independent infrastructure; deserves its own message.
*Operator call:* peek at the file or recall the intent, then say "fold" or "separate."

### F2 — Wave B vs Wave C ordering

Convention question: do **proposal directories commit before** their **graduated skill directories**, to make the audit trail "proposal → skill"? Or does it not matter because both reference the same SHAs in their pointers?
*Operator call:* commit C-before-B (proposal-first), or any order.

### F3 — Modified proposal.json files (D1)

`prop_2026-04-30_verifier-for-dashboard/proposal.json` (27 lines) and `prop_2026-04-30_verifier-for-regime-audit-report/proposal.json` (25 lines) have substantial diffs that are NOT pure renaming. Agent has not read what changed. Should the operator review these diffs before they get folded into the D1 vocabulary-lift commit, or split them into a separate "proposal-state updates" commit?
*Operator call:* "fold into D1 trusting the diff," or "show me the diffs first."

### F4 — `skills/claim_audit/{datasets,outputs}/` (untracked)

Runtime emission directories from claim_audit runs. Convention from `skills/gap_audit/datasets/` suggests datasets get committed (with `.source_state` siblings) for reproducibility, but `outputs/` typically holds run-specific artifacts that may belong in `.gitignore`.
*Operator call:* commit datasets but gitignore outputs; or commit both; or gitignore both.

### F5 — Render outputs (REVIEW.html / REVIEW.md)

These re-emit from `tools/render_proposals*.py`. Two options:
- **Fold into A7** — render outputs ship with renderer changes.
- **Separate commit "regenerated REVIEW pages"** — keeps the renderer change pure.
*Operator call:* fold or separate.

### F6 — `.claude/` directory commit policy

Does `.claude/` belong in the repo? If yes, what's safe to commit (settings.local.json may have machine-specific paths or secrets) and what should `.gitignore`?
*Operator call:* commit in I1, defer with a `.gitignore` entry, or partial-commit specific subfiles.

### F7 — `overnight_log.jsonl` commit policy

Does the overnight log belong in version control or in a gitignored runtime path? If versioned, naming becomes important (it's currently at root with no date in filename).
*Operator call:* commit, gitignore, or rename + commit.

---

## Quick-pick path (if you want a default)

If you want a one-line answer to *"just do the safest thing":*

> **Wave A1 → A2 → A3 → A4 → A5 → A6 → A7 → A8 → A9 (skip F1: leave receipts.py untracked for separate review). Then C2 → B1 (proposal before skill). Then C1, C3, C4. Then E1. Then F1 (gap-collector wave). Defer everything in "Flagged items," the new skills B2/B3/B4, modified D1 proposals, tools G1, meeting-notes H1/H2, and operator infra I1/I2/I3 to a follow-up digest after Wave A is in.**

That closes the highest-stakes wave (the vocabulary lift + grading events) cleanly, captures the new symphony skill+proposal as a paired commit, lands gap-audit substrate, and lets us look harder at the rest in a smaller second pass.

---

## What this digest is NOT

- **Not** an authorization to commit. The operator's response below this line authorizes specific groups.
- **Not** signed by the operator. Agent-authored decision surface; operator response is the green light.
- **Not** a substitute for the heartbeat skill. This is a one-shot manual sweep. The skill build (with `drift_accumulation` gap collector, proposal, candidate, graduation) remains the longer path documented in [meeting-notes/2026-05-01-heartbeat-frame.md](../meeting-notes/2026-05-01-heartbeat-frame.md).

## Operator response (write below)

*(Block reserved for operator. Name the groups to commit, or refine the digest, or push back on any flagged item. Agent reads this block as the green light.)*
