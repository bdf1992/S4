# Boards inventory

A pass over the repo asking, *for each file or directory, is this carrying workflow state that wants to be a kanban card, or is it a specification / runbook / single-instance config that should stay prose?* Workflow state = a thing with `status`-shaped (or column-shaped) life over time. Specs don't move; cards do.

This file is itself a draft inventory; the operator marks which entries are in-scope before adapters are built. Lower-priority candidates can be deferred until the upstream artifacts grow enough records to justify a board view.

## Section 1 — Already board-shaped on disk (adapter + render only)

These already carry the structure a board needs. The cost to "board them" is one thin adapter that projects the source into the baseline card schema.

| Source | Column axis | Lane axis | Card identity | Records today | Priority |
| --- | --- | --- | --- | --- | --- |
| `debts/D-*.json` | `status` (open / parked / closed_paid / closed_written_off / superseded) | `severity` (load_bearing / cosmetic / unknown) | one debt | 5 | **HIGH** — first board, validates the pattern |
| `skills/leash_*/exemplars/{proposed, promoted}/` | directory itself (proposed → promoted is the column transition) | (none yet) | one exemplar bundle | 1 proposed in hooks leash, 0 promoted; 0/0 in slash leash | MEDIUM — useful when the operator starts promoting |
| `skills/leash_*/outputs/run-*/` | `manifest.claim` (0.4 / candidate / rejected / unleashed) | `manifest.leash_state.state` (on / off / scoped) | one bundle | many; regenerable | LOW — this is regenerable telemetry; useful for trend-spotting, not for deciding-and-doing |

## Section 2 — Could be board-shaped with light restructure

These hold workflow state today but in a shape that fights the kanban projection. Each becomes a board after a small structural change.

| Source | What's there now | Restructure needed | Column axis | Card identity | Priority |
| --- | --- | --- | --- | --- | --- |
| `foundations/grading-events.md` | One markdown file with `## Event NNN` H2 sections, one per event. | Either (a) split into `foundations/grading-events/E-NNN.md` per-event files with frontmatter, or (b) keep flat and have the adapter parse H2 sections (more brittle but no source change). | `status` (PENDING / RESOLVED / REJECTED / SUPERSEDED) | one grading event | **HIGH** — second board after debts, exercises the recursion (proves baseline schema works across two unrelated artifacts) |
| `meeting-notes/*.md` | One file per note; some are dated transcripts, some are runbooks (`narrator-console.md`). Each has a date, subject, and citation-tier role. | Add a small frontmatter block per note (`date`, `subject`, `kind: transcript | handoff | reference`, `status: active | settled`). Or have the adapter infer from filename + first H1. | `kind` × `status` (or `kind` alone — transcripts/handoffs/references) | one note | MEDIUM — useful but the directory is small (4 files); might wait until it's bigger |
| **leash registry (does not exist yet)** | No artifact today. Each leash directory is its own implicit record. | Create `leashes/registry.json` (or auto-generate by walking `skills/leash_*/`). One record per leash with surface, last-verify-status, toggle state, exemplar count, claim distribution. | `last_verify_status` (clean / failing / unrun) or `surface` | one leash | MEDIUM — useful at ≥2 leashes (we're at 2); enables the cross-leash registry your recursion-seam mentions as future work |
| `skills/subprotocol-for-claude-code/reports/sync-*.md` | One report (`sync-2026-04-29.md`) so far. Each is a periodic sync against the SubProtocol upstream. | If more reports accrete, add a `status` (sync-clean / sync-divergence) and date frontmatter; adapter projects to a card. | `status` if introduced; otherwise `date` (chronological) | one sync report | LOW — only one record today; revisit when there are 3+ |

## Section 3 — Stays prose (not board-shaped)

These are specs, runbooks, single-instance configs, or pure code/data. Forcing them into a board projection misframes them — they don't have lifecycle status that moves.

- `CLAUDE.md`, `README.md` — project-level highest-abstraction docs.
- `foundations/{data-point, collection-program, pointer, zero-four}.md` — immutable specs.
- `foundations/llm-sdk-denylist.txt` — source data walked by a collector; canonical, not workflow.
- `boards/schema.md` (when written), `debts/schema.md` — schema/convention docs.
- `skills/leash_*/SKILL.md`, `recursion-seam.md`, `orchestrate.py`, `verify.py`, `leash_state.json` — per-leash single-instance config and code.
- `skills/leash_*/collectors/`, `lib/`, `resolvers/`, `signals/` — code modules.
- `skills/leash_*/references/*.txt` — taxonomy source data.
- `skills/leash_*/datasets/` — collector outputs (regenerable; not workflow state).
- `skills/regime_audit/` — too early to judge; only `lib/data_point.py` exists. Revisit when the skill takes shape.
- `skills/subprotocol-for-claude-code/{SKILL.md, overlay.md, references/, scripts/}` — single-instance skill, code, and config.
- `meeting-notes/narrator-console.md` — runbook of operator commands (could become a "narrator-command" board if it accretes use, but not now).

## Section 4 — Open questions

1. **Restructure `grading-events.md` or parse-in-place?** Splitting into per-event files is more agent-native but rewrites a file the operator just committed. Parsing in place keeps the source untouched but introduces a brittler adapter. *Operator decides.*
2. **Frontmatter on meeting-notes?** Adding `date`/`subject`/`kind`/`status` to existing notes is a small touch but propagates a convention. Worth it if meeting-notes accretes; overkill at 4 files. *Defer until more notes exist.*
3. **Leash registry: file or computed view?** A `leashes/registry.json` checked into git vs. a script that walks `skills/leash_*/` at render time. Computed view is more agent-native (per the artifact-skill split: don't persist what can be re-derived from source). *Lean computed view; revisit if we need cross-leash invariants enforced at commit time.*
4. **Per-source `last_updated_at` derivation.** For the baseline card schema, should `last_updated_at` come from (a) a field on the source record, (b) `git log -1 -- <file>`, or (c) filesystem mtime? `git log` is most honest; mtime is fastest; the source field is most explicit. *Lean `git log` for files committed; source field for live records like debts.*

## Proposed in-scope set for the first iteration

The smallest set that exercises the pattern enough to validate the baseline schema:

1. **debts/** — Section 1, HIGH. Already board-shaped.
2. **foundations/grading-events.md** — Section 2, HIGH. Tests the multi-record-in-one-file adapter pattern (or motivates the per-event-file split).
3. **leashes registry (computed)** — Section 2, MEDIUM. Tests an artifact that doesn't exist on disk and is computed at render time.

Three boards, three different shapes (structured records / parsed prose / computed view), all sharing one baseline card schema. If the schema fits all three cleanly, it's load-bearing; if not, the misfit tells us something real.

The remainder of Section 1 and 2 entries get adapters when their upstream accretes enough records to be worth viewing.
