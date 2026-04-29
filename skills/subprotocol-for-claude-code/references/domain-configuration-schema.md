# Domain Configuration Schema

`domain-configuration.yaml` is the user's tuning surface. It carries the per-project fills for each active slot's `domain_configuration` block in [`section-taxonomy.md`](../../system-prompt-shape/references/section-taxonomy.md). One file per project.

`sync.py` reads it on every run; the overlay text is downstream. Edit this file, run `sync`, see the overlay change. Do not edit the overlay region in `CLAUDE.md` directly.

## Top-level shape

```yaml
project:
  name: string                          # human-readable project name; appears in overlay header
  domain: string                        # short domain slug; e.g. "game-dev", "legal-review", "academic-writing"
  customization_filename: string        # default "CLAUDE.md"; override for non-standard host file
  overlay_marker_start: string          # default literal: "<!-- SUBPROTOCOL:OVERLAY:START — generated, do not edit between markers -->"
  overlay_marker_end: string            # default literal: "<!-- SUBPROTOCOL:OVERLAY:END -->"

slots:                                  # one entry per slot the user is opting into
  <slot-name>:
    enabled: boolean                    # required; false skips this slot entirely
    change_response: enum               # optional override; default comes from section-taxonomy.md
    fills: map                          # required when enabled; matches the slot's domain_configuration shape
```

NOOP slots (`persona`, `global-safety-and-refusal`, `session-and-help-meta`) do not appear in `slots:` — they have `change_response: block` and never render. Listing them is a no-op; omitting them is the convention.

## Per-slot fill shapes

Each slot's `fills:` block must match the `domain_configuration` shape declared in [`section-taxonomy.md`](../../system-prompt-shape/references/section-taxonomy.md). Below are the shapes for the most common slots; consult the taxonomy for the authoritative list.

### slot 2 — engineering-task-discipline

```yaml
engineering-task-discipline:
  enabled: true
  fills:
    registry_path: string               # filesystem path; e.g. "definitions/"
    asset_kinds: list[string]           # domain nouns; e.g. ["module", "scene", "system", "tool"]
    pointer_format: string              # citation form; default "file_path:line_number" for Claude Code
    source_layout:
      source_root: string               # e.g. "src/"
      definitions_root: string          # e.g. "definitions/"
      tests_root: string                # e.g. "tests/"
```

### slot 3 — tool-use-discipline

```yaml
tool-use-discipline:
  enabled: true
  fills:
    subprotocol_tools:                  # SubProtocol tools advertised in Claude Code's tool-use register
      - name: string                    # e.g. "definition_lookup"
        purpose: string                 # one-line description
    parallel_invocation_examples: list[string]
```

### slot 4 — autonomy-and-action-discipline

```yaml
autonomy-and-action-discipline:
  enabled: true
  fills:
    risk_classes: list[string]          # e.g. ["asset_delete", "registry_rewrite", "schema_change"]
    confirm_threshold: enum             # "always" | "named-risk-classes" | "never"
    source_walk_first: boolean          # default true
```

### slot 5 — git-rules

```yaml
git-rules:
  enabled: true
  fills:
    commit_message_template: string     # template with {pointer_format} substitutions
    pr_evidence_path: string            # e.g. "evidence/" or "reports/pr-evidence/"
```

### slot 7 — formatting-and-output-style

```yaml
formatting-and-output-style:
  enabled: true
  fills:
    citation_format: string             # default "file_path:line_number"
    end_of_turn_summary_includes_asset_kind: boolean
```

### slot 8a — host-templated-data-runtime

```yaml
host-templated-data-runtime:
  enabled: true
  fills:
    injection_keys: list[string]        # additions to Claude Code's # Environment block
    subprotocol_substrate:
      registry_summary: object          # what to publish; e.g. {kinds_count, recent_definitions_n: 5}
      open_requests: object
      recent_definitions: object
```

### slot 11 — memory-subsystem (Claude Code only)

```yaml
memory-subsystem:
  enabled: true
  fills:
    subprotocol_memory_kinds: list[string]
    memory_save_template: string        # uses pointer_format
```

### slot 13 — planning-procedure

```yaml
planning-procedure:
  enabled: true
  fills:
    plan_template: string               # markdown numbered list
    pre_act_check: list[string]         # checks before each plan step
```

### slot 20 — procedure (SubProtocol-introduced)

```yaml
procedure:
  enabled: true
  fills:
    procedure_kinds:                    # ordered list of named procedures
      - name: string                    # e.g. "scene-add"
        trigger: string                 # human-readable when this procedure runs
        steps:                          # ordered list
          - body: string                # imperative step
            branch_on: string           # optional; condition that branches flow
        judgment_seams:                 # optional; named decision points
          - seam_name: string
            condition: string
            options: list[string]
        exit_conditions: list[string]   # optional; when procedure terminates early
```

### slot 21 — render (SubProtocol-introduced)

```yaml
render:
  enabled: true
  fills:
    render_kinds:
      - name: string                    # e.g. "scene-graph-diagram"
        format: enum                    # "mermaid" | "svg-json" | "markdown-table" | "narrated-prose"
        trigger: enum                   # "on-request" | "on-pointer-resolution" | "on-pre-commit" |
                                        # "on-substrate-publish" | "on-end-of-turn"
        path: string                    # filesystem path for the regenerable artifact
        recompute_threshold: enum       # "per-turn" | "per-N-turns" | "per-session" | "on-trigger"
```

## Validation

`sync.py` validates `domain-configuration.yaml` before rendering:

1. **Required keys present.** `project.name`, `project.domain`, at least one slot enabled.
2. **Slot names recognized.** Every key under `slots:` matches a slot in the section taxonomy.
3. **Required fills present.** Each enabled slot's `fills:` covers every required key in the slot's `domain_configuration` shape.
4. **Type checks.** Lists are lists, maps are maps, enum values are in the enum set.
5. **Cross-slot consistency.**
   - `registry_path` referenced from multiple slots must be the same string.
   - `pointer_format` is consistent across slots that use it.
   - Procedure step bodies that reference asset kinds use kinds declared in slot 2's `asset_kinds`.

Validation failures abort sync with a non-zero exit and a report at `reports/sync-errors-{date}.md`. The overlay region in `CLAUDE.md` is left unchanged on failure.

## Migration

When the section taxonomy adds a slot or changes a slot's `domain_configuration` shape:

1. `sync.py` flags missing required fills as a validation error.
2. The user adds the new fills (or runs `setup-interview.py` to have them proposed from the existing repo).
3. Existing fills for unchanged slots survive untouched.

The configuration file is the durable artifact. The overlay text is regenerable; the configuration is not.

## Sample

See [`domain-configuration.yaml`](domain-configuration.yaml) in this directory for the game-team scenario fill — a working example that exercises slots 2, 3, 4, 5, 7, 8a, 11, 13, 20, 21.
