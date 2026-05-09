# Board card schema

This file formalizes the baseline card schema the `boards/` system uses across every adapter. Until this file existed, the schema was implicit in [boards/__main__.py](__main__.py), the per-adapter `cards()` returns, and [boards/lib/cards.py:cards_from_dataset](lib/cards.py) — readable but unciteable. This was tracked as [debts/D-006.json](../debts/D-006.json).

The schema below names each field, what it represents, and the kanban tradition the design borrows from. Citations are to published practitioner sources, not internal prose.

## Two shapes

A card travels through two shapes inside this system:

- **Source shape** (canonical) — emitted by a `boards/collectors/<name>_cards.py` Foundation-2 collector. Persisted as JSONL data points under `boards/datasets/<name>_cards.jsonl`. Field names match the design vocabulary: `column` (workflow position), `lane` (categorical axis), `payload` (per-source fields).
- **Render shape** (projection) — produced by [boards/lib/cards.py:cards_from_dataset](lib/cards.py) for the markdown and HTML renderers. The projection maps `column → status`, `lane → severity`, and flattens `payload` into the top-level dict. `status`/`severity` are render-ergonomic names; the canonical names are `column`/`lane`.

Both shapes carry the same information. The split exists because renderers want a flat dict; collectors emit a structured one.

## Baseline fields (source shape)

| Field | Type | Required | Source-of-truth |
|---|---|---|---|
| `card_id` | string | yes | a stable identifier the source uses for this record (e.g., `D-001`, `E-007`, a directory name) |
| `subject` | string | yes | one-line description of what the card is about |
| `column` | string | yes | the card's workflow position; must be in the board's declared `columns` list (see [boards/__main__.py:BOARDS](__main__.py)) |
| `lane` | string \| null | yes if `lanes: true` in BOARDS | categorical axis (e.g., `severity` for debts, `kind` elsewhere); null if the board doesn't use lanes |
| `last_updated_at` | string (ISO 8601 date) | yes | YYYY-MM-DD; when the underlying source last changed (per source field, or `git log -1 -- <file>`) |
| `payload` | object | optional | per-source domain fields, projected verbatim onto the render dict (e.g., `payoff`, `principal`, `interest`, `depends_on`, `re_trigger`) |

## Tradition citations

### Column axis = workflow state

**Source:** David J. Anderson, *Kanban: Successful Evolutionary Change for Your Technology Business*, Blue Hole Press, 2010 (https://www.davidjanderson.com/kanban-book/).

Anderson's framing: the column is the workflow stage a unit of work is in *right now*. Work flows left-to-right through columns; each column has a Work-In-Progress limit (we don't enforce WIP today, but the column-as-state design admits it as a future axis). Each board declares its own column set in [boards/__main__.py:BOARDS](__main__.py) — debts use `open / parked / closed_paid / closed_written_off / superseded`; grading-events use `pending / approved / resolved / rejected / superseded`; etc. Status semantics belong to each source's domain (debts/schema.md, foundations/grading-events.md).

### Lane axis = categorical projection

**Source:** Anderson 2010, §"Swimlanes"; also widely conventionalized by Atlassian Jira (https://support.atlassian.com/jira-software-cloud/docs/configure-swimlanes/).

A swimlane is a horizontal partition of the board, orthogonal to the column axis. We use it for severity in the debts board (`load_bearing` vs `cosmetic` vs `unknown`) so reviewers can scan one lane to see the load-bearing-open work without being distracted by cosmetic items. Lanes are optional per board (boolean `lanes: true` in BOARDS); when absent, the card's `lane` is null and the renderer collapses to a single-row layout.

### Cumulative flow at the meta-board (`needs_attention` vs `healthy`)

**Source:** Eric Ries, *The Lean Startup*, Crown Business, 2011, ch. on innovation accounting; cumulative flow diagrams (CFDs) are an older kanban concept formalized by Anderson 2010 §"Cumulative Flow Diagram".

The meta-board ([boards/adapters/all_boards.py](adapters/all_boards.py)) summarizes every leaf board as one card with a binary status: `needs_attention` if the leaf has any open + load-bearing item, else `healthy`. This is the simplest legible cumulative-flow projection — it answers "is anything urgent?" without showing the trend. The full CFD with stacked area over time lives in [skills/dashboard/html.py](../skills/dashboard/html.py) as the proposal-flow visualization; the meta-board's summary is its operator-friendly headline.

### `depends_on` / `blocks` edges

**Source:** Atlassian Jira's epic / story / sub-task relation model (https://support.atlassian.com/jira-software-cloud/docs/what-are-issue-types/) — `Blocks`, `Is blocked by`, `Relates to`.

Cards may carry a `depends_on: [card_id, ...]` field in their `payload`. The relation is one-way: A `depends_on` B means A cannot close before B closes. Renderers may show edges; the dashboard's debt section ([skills/dashboard/render.py](../skills/dashboard/render.py)) currently doesn't, but the data is in the dataset for any future renderer.

We do not (yet) implement `blocks` as a separate field — it would be the inverse of `depends_on` and computable, not authored. Adding it would be a follow-up if a renderer needs cheap reverse-lookup.

## What's not in the schema

- **WIP limits per column.** Anderson's Kanban Method centers on these. We don't track or enforce them today. Adding them would mean per-column-per-board limits in BOARDS plus a dashboard panel that reports breaches.
- **Cycle time / lead time.** Computable from `last_updated_at` deltas across column transitions if we tracked transitions. Today we only see the current column, not its history.
- **Card priority.** No `priority` field. Severity (lane) plus column position are the only ranking axes.
- **Assignees, due dates, comments.** Github Issues handle these for Symphony-dispatched work. Internal boards (debts, grading-events) don't need them.

These are intentional omissions — the boards system is a kanban-for-derived-data, not a project management tool. If a future use case requires WIP enforcement or cycle time, the schema extends; the omission is the floor today.

## Validation

[debts/validate.py](../debts/validate.py) validates the debts source. Each adapter's collector ([boards/collectors/](collectors/)) is the equivalent for its board — it walks the source files, projects them into the source shape, and refuses to emit a card that's missing a required field. The `boards/datasets/<name>_cards.source_state` file alongside each dataset is a content hash of the inputs; mismatched state means the dataset is stale and the collector needs to be re-run.

## Promotion path

Per [debts/schema.md](../debts/schema.md) §"Promotion path": if this artifact earns its keep — used by both leashes, referenced during gap-handling — promotion to **Foundation 5** in a logged grading event is the natural next move. Until then it's a sub-foundation primitive that the existing foundations don't depend on. Same applies to this `boards/schema.md` file — it grounds geometry today; it earns Foundation status when the geometry is load-bearing for an external consumer.
