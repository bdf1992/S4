# Recursion seam — when, and then how, additional leash apparatus is built

CLAUDE.md says: *"the leash also carries the capacity to produce more leashes (and other harness extensions: new skills, new slash commands, new hooks) for sibling harness surfaces, each new leash bedrock-conforming and ladder-disciplined by the same rules."*

The skeleton of `leash_for_hooks` is parameterized by **surface** (which Claude Code harness surface the leash constrains), so the *how* of producing a sibling is mechanical: a structural copy-and-substitute that touches a small, declared set of seams, with everything in [lib/](lib/) shared verbatim. The mechanical steps are documented later in this file.

The *when* is upstream of that and is the more important question: under what conditions should a sibling leash (or any new harness apparatus) be built at all? The next section answers it. The mechanical steps only run after a signal motivating them has fired.

## When the seam fires (the operator-side gate)

The recursion seam is **0.2-shaped, not 0.3-shaped** — it is a signal whose verdict the operator consults, not an orchestration that emits new leashes. The default is **no growth**: apparatus is added (or retrained, or repaired, or replaced) only when the existing apparatus's own measurements indicate it is no longer sufficient for what the operator is asking of it.

This is the same principle as CLAUDE.md's *"0.4 is driven by 0.2, not by request,"* extended one level up. The bedrock decides whether a 0.4 emission is permitted from inside a leash; the same logic applies to whether *the existence of a new leash* is permitted from outside one. The signal informs; the operator decides; the system never silently produces additional apparatus.

Five outcomes the operator can take when consulting the signals from existing leashes. Each corresponds to a different shape of gap-record from the existing leash — or, in the last case, from the operator's session history.

**1. Leave alone (default).** The leash's emission gate fires `ready` when it should; gap_records are sparse; `verify.py` exits clean; the source the collectors walk is fresh. No action. Most of the time this is the correct outcome. Silence from signals is not stalled growth — it is the bedrock saying nothing needs to change.

**2. Retrain (existing leash, wider corpus).** The structural shape is correct but the dataset is too thin or stale.
- *Gap-record:* repeated `not_ready` from `emission_readiness` with the same `shortfall_per_kind` over many runs, or persistent `insufficient_training_exemplars` with no new promotions arriving.
- *Action:* grow the corpus the existing collectors walk (more user-authored hooks, more exemplars promoted), then re-run. No new files; no new leash.

**3. Repair (specific 0.1 collector or 0.2 signal).** A component is drifting against the source it tracks.
- *Gap-record:* a collector's `verify()` returning `dangling` on a high fraction of previously-emitted data points (the source moved under it); a signal's probe set still passing but its real-world verdicts contradicting accumulated operator approvals; an audit-budget violation newly appearing.
- *Action:* fix the specific component. The leash itself remains.

**4. Replace (the leash is the wrong shape for its surface).** The surface has shifted, or the original shape was a misfit.
- *Gap-record:* persistent `rejected` / `unleashed` at high rates with no obvious operator misuse; multiple distinct `gap_record.reason` values accumulating across runs; the surface taxonomy has changed enough that the dataset-membership decision no longer maps cleanly.
- *Action:* the existing leash informs the new one — its data, its 0.2 fits, its accumulated gap_records become inputs to the new leash's design — but is otherwise discarded. This is the upgrade path.

**5. Build new alongside (a different surface).** The signal is not from inside any existing leash; it is a meta-signal across the operator's hand-walked work.
- *Gap-record:* the operator is repeatedly applying ladder discipline by hand to a surface no existing leash covers. Every time the same shape of ad-hoc verification gets re-derived, that recurrence is the signal that a new leash should formalize it.
- *Action:* run the mechanical steps below for the new surface.

The signal-source for outcomes 2–4 lives **inside** the existing leash (its own datasets, signals, and verify output). The signal-source for outcome 5 lives in the **operator's session history** — what gets done by hand repeatedly. Both are real signals; neither is a request alone. Until one of them fires, the seam stays closed and no new apparatus is produced.

## What is shared (verbatim across all sibling leashes)

These files are **bedrock-shared**. A sibling leash imports them; it does not reimplement them. If a sibling leash needs to change anything in this list, that's a 0.4 grading event on the foundations themselves, not a sibling-private change.

- [foundations/data-point.md](../../foundations/data-point.md), [foundations/collection-program.md](../../foundations/collection-program.md), [foundations/pointer.md](../../foundations/pointer.md), [foundations/zero-four.md](../../foundations/zero-four.md) — the bedrock spec.
- [foundations/llm-sdk-denylist.txt](../../foundations/llm-sdk-denylist.txt) — the SDK denylist source.
- [lib/data_point.py](lib/data_point.py), [lib/collection_program.py](lib/collection_program.py), [lib/pointer.py](lib/pointer.py), [lib/audit.py](lib/audit.py), [lib/leash_state.py](lib/leash_state.py) — the validators, constructors, and toggle reader. *Future refactor: lift these to a top-level `bedrock/` package so siblings import from one place rather than a sibling-private `lib/`.*
- [collectors/llm_sdk_denylist.py](collectors/llm_sdk_denylist.py) — the recursive-fence denylist collector. Walks the same `foundations/llm-sdk-denylist.txt` regardless of which surface a sibling targets.
- [resolvers/file_line.py](resolvers/file_line.py), [resolvers/collector.py](resolvers/collector.py), [resolvers/data_point.py](resolvers/data_point.py) — the three universal pointer kinds.

## What changes per surface (the seams)

These are the only structural slots a sibling leash fills in. Each is a small, well-typed change.

### 1. Surface-specific source taxonomy reference (analogous to `references/hook-events.txt`)

Each surface has a *closed enumeration of legal shapes* the leash treats as its taxonomy:
- **hooks** → event names (`PreToolUse`, etc.) — declared in [references/hook-events.txt](references/hook-events.txt).
- **slash-commands** → reserved/disallowed names, namespace prefixes, max-arg counts.
- **MCP wirings** → recognized transports (`stdio`, `sse`), required handshake fields.
- **CLAUDE.md sections** → the section taxonomy (subprotocol-for-claude-code already pioneered this with `section-taxonomy.md`).
- **agent definitions** → required frontmatter fields, recognized model values, recognized tools.

The sibling leash carries a `references/<surface>-taxonomy.txt` and a `collectors/<surface>_decl.py` collector that walks it. The shape is identical to [collectors/hook_event_decl.py](collectors/hook_event_decl.py); only the constants change.

### 2. Surface-specific config collector (analogous to `collectors/hook_config.py`)

Each surface has 1-N file paths the user uses to configure that surface:
- **hooks** → `~/.claude/settings.json`'s `hooks` block (and three sibling locations) — [collectors/hook_config.py](collectors/hook_config.py).
- **slash-commands** → `~/.claude/commands/*.md`, `<repo>/.claude/commands/*.md`, plugin command directories.
- **MCP wirings** → `~/.claude.json` (Claude Desktop) or the CLI MCP config.
- **CLAUDE.md sections** → `<repo>/CLAUDE.md`, `~/.claude/CLAUDE.md`, sub-CLAUDE.md files.
- **agent definitions** → `~/.claude/agents/*.md`, `<repo>/.claude/agents/*.md`.

The sibling leash carries `collectors/<surface>_config.py` whose shape is identical to `hook_config.py`: declared INPUTS as paths/globs, `_discover()` walks the resolved set, `_walk_<surface>(path) -> list[value_dict]` parses each, `collect()` assembles data points, `verify()` round-trips a single record.

### 3. Surface-specific signals (analogous to `signals/hook_collision.py`)

Each surface has at least one signal that answers "does this candidate collide with / shadow / contradict an existing one?". The shape is identical:
- `fit(training_rows) -> fitted_params` — typically a set or histogram.
- `evaluate(candidate, *, fitted_params, training_rows) -> {verdict, confidence, evidence_pointers}`.
- `PROBES` — at least 2 (one collision, one clear).
- `run_probes()` — wraps the literal probe set for verify.py.

The verdict enum is per-surface but always small. `signals/emission_readiness.py` is shared verbatim — its `MIN_EXEMPLARS = 50` rule is the same regardless of which surface the leash targets, because what it measures is "do we have enough exemplar bundle states yet?", not anything surface-specific.

### 4. The orchestration's DECISION_POINTS (analogous to `orchestrate.py`)

Each leash declares its own ordered decision points. The pattern:

```python
DECISION_POINTS = [
    ("<thing>_validity",  "<surface>_decl"),       # 0.1 dataset membership
    ("collision_check",   "<surface>_collision"),  # 0.2 surface-specific signal
    ("emission_gate",     "emission_readiness"),   # 0.2 shared signal
]
```

For most surfaces, three decision points are enough. Add more if the surface has more shape-validation steps (e.g. MCP wirings might want a `transport_validity` and a `handshake_check`).

### 5. `leash_state.json` (per-surface toggle file, same shape across siblings)

Each sibling carries its own [leash_state.json](leash_state.json) at the skill root. The shape is identical across surfaces — `{state: "on"|"off"|"scoped", scoped_on_events?: [...]}` — and validated by the shared [lib/leash_state.py](lib/leash_state.py). The *file is per-surface* because the operator may want different toggles on different surfaces (e.g., leash-on for hooks, leash-off for slash commands once trusted). The validator is shared verbatim across siblings; the toggle gate call in `orchestrate.py` is near-verbatim — each leash passes `key=` to `ls.is_leashed()` to name its candidate's identity field (`"event"` for hooks, `"name"` for slash commands). Only that one argument and the file's contents (the surface-specific scoped event names) vary.

### 6. SKILL.md surface identifier (in body prose, not frontmatter)

The Anthropic Agent Skill spec's frontmatter has a fixed schema (`name`, `description`, `when_to_use`, `argument-hint`, `allowed-tools`, `license`); there is no `metadata:` block and no `surface:` field. Earlier drafts of [SKILL.md](SKILL.md) carried an invented metadata block with `surface:`; the current SKILL.md captures the surface in a body-level "About this skill" line:

```markdown
> **About this skill** — surface: `<claude-code-surface-name>` · rides under: Claude Code · category: harness-control · pattern: ladder-disciplined-leash. License: MIT.
```

This is the load-bearing identifier; sibling leashes declare their surface here. Two leashes with the same surface conflict and `verify.py` should reject (a future cross-leash check that parses the line, since it's no longer a structured frontmatter field).

## What a sibling leash looks like, concretely

Spawning a sibling leash for, say, slash commands:

1. Create `skills/leash_for_slash_commands/` with the same top-level layout.
2. Copy [SKILL.md](SKILL.md) → adjust frontmatter `surface: slash-commands`, descriptions.
3. Copy [recursion-seam.md](recursion-seam.md) → leave verbatim (it documents the same pattern).
4. Symlink or import-from `lib/`, `resolvers/`, `collectors/llm_sdk_denylist.py`, `signals/emission_readiness.py` from a shared package (or copy initially; refactor to shared once a third leash exists — three is the threshold for de-duplication).
5. Create `leash_state.json` with `{"state": "on"}` (the safe default).
6. Create `references/slash-command-taxonomy.txt` (reserved names, prefixes).
7. Create `collectors/slash_command_decl.py` — same shape as `hook_event_decl.py`, INPUTS pointing at the new taxonomy file.
8. Create `collectors/slash_command_config.py` — same shape as `hook_config.py`, INPUTS pointing at `~/.claude/commands/*.md` and project-local equivalents.
9. Create `signals/slash_command_collision.py` — same shape as `hook_collision.py`, fitted on `slash_command_config` data points.
10. Create `orchestrate.py` — same shape, with `DECISION_POINTS` updated to reference the new fence ids. The toggle gate (`toggle_check` consulting `leash_state`) is structurally identical and ported verbatim.
11. Create `verify.py` — copy of [verify.py](verify.py), with `COLLECTORS` and `SIGNALS` tuples updated to reference the slash-command-specific modules.

The 10 steps are mechanical. The actual *engineering* in a sibling leash is in (a) what shape the surface's data points have (= the value_schema), (b) what the surface's collision rule is, and (c) what the taxonomy file contains. Everything else is structural copy-and-substitute.

## Why "more leashes" is the success indicator, not "first 0.4 bundle"

CLAUDE.md says floor-growth is the metric: the per-round generative share should shrink as the floor grows. The seam above is the mechanism:

- Round 1 (this leash): the entire 0.1 layer is built from scratch. 4 collectors, 3 resolvers, 4 lib modules, 1 reference taxonomy. Generative share is high.
- Round 2 (sibling leash for slash-commands): all of `lib/`, `resolvers/`, `collectors/llm_sdk_denylist.py`, `signals/emission_readiness.py` are reused verbatim — the floor. Only the surface-specific seams (steps 5–9 above) are new. Generative share is much smaller.
- Round 3 (sibling leash for MCP wirings): same again. By now the lift-to-shared refactor (step 4 above) has happened; siblings import from a shared `bedrock/` package; generative share is purely surface-specific shape and rules.

If round 3's generative share is *not* meaningfully smaller than round 1's, the seam is wrong (or the foundations are too thin), and that itself is a 0.4 grading event on the foundations. *That* is what makes the floor-growth metric falsifiable.

Floor-growth is a metric *given that signals are firing for new rounds*. If no signal fires (no surface is being hand-walked repeatedly, no gap-record is accumulating, no existing leash is drifting), there is no round N+1 and the metric is undefined for that period — not failed. Absence of recursion in the absence of a signal is the correct state of a healthy system. The metric falsifies only when a round happens *and* the per-round generative share fails to shrink.

## What this leash does NOT yet have (work for follow-on leashes or siblings)

- **A cross-leash registry.** When sibling leashes exist, a top-level `skills/registry.json` should enumerate them by surface, so verify.py can check no two leashes claim the same surface.
- **A shared bedrock package.** Currently `lib/` is sibling-local. Once a second leash exists, lift to `bedrock/`.
- **A leash-of-leashes** (the meta-leash). When the seam above is itself stable across 2–3 sibling leashes, the meta-leash generates a sibling from a single declaration of `(surface_name, taxonomy_path, config_globs, collision_rule)`. That meta-leash is what makes the recursion truly hands-off; it is explicitly a v0.3 deliverable.
