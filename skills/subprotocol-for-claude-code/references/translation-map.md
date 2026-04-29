# Translation Map — SubProtocol → Claude Code register

Per [feedback_subprotocol_uses_host_vocabulary](../../../../C:/Users/bdf19/.claude/projects/c--Users-bdf19-Desktop-SubProtocol/memory/feedback_subprotocol_uses_host_vocabulary.md): overlay text uses ONLY Claude Code's existing words. SubProtocol's abstract vocabulary stays internal to the skill — `domain-configuration.yaml`, `section-taxonomy.md`, the principle memories. The render step translates through this map before any text lands in `CLAUDE.md`.

The rule: if a SubProtocol term has a Claude Code equivalent, use the Claude Code term. If it doesn't, find the closest Claude Code register and frame the new behavior in Claude Code's idiom (imperative bullet, `IMPORTANT:` prefix when load-bearing, file path citations, etc.) rather than introducing the SubProtocol term.

## Vocabulary table

| SubProtocol internal | Claude Code register | Notes |
|---|---|---|
| `request` | `task` | Claude Code's "Doing tasks" frames work as task-completion. |
| `asset` | (use the user's domain noun — see `domain-configuration.yaml`'s `asset_kinds`) | "Asset" never appears in overlay text. Game team: `module`, `scene`, `system`, `tool`. Legal team: `clause`, `precedent`, `template`. |
| `pointer` | `file_path:line_number` (or `[filename.ts](src/filename.ts#L42)` in markdown contexts) | Claude Code's existing citation form per its VSCode-extension instructions. |
| `pointer_lookup` | "search" or "walk" (verbs) | "Walk `definitions/`" — Claude Code uses Glob, Grep, Read; "walk" is the natural register. |
| `pointer_emit` | "cite by `file_path:line_number`" | Claude Code never says "emit pointer." |
| `definition_compute` | "compute" or "derive" | Mechanism stays implicit; the bullet describes the behavior, not the term. |
| `registry` | (use the user's `registry_path` directly — e.g. `definitions/`, `lore/`, `clauses/`) | "Registry" never appears in overlay text. The path is concrete; the abstraction is not surfaced. |
| `register` (verb) | "save under" / "place in" | "When generating, save the new module under `definitions/scenes/`." |
| `kind` | (use the user's specific kind name — `module`, `scene`, `clause`) | "Kind" never appears. The kinds are listed by name. |
| `proof` | "evidence" or "verification step" | Claude Code's git-rules talk about evidence trails; SubProtocol's "proof" maps onto this. |
| `definition` (noun) | (use the user's domain noun for the computed artifact) | When unavoidable, "computed summary" or "derived index." |
| `render` (noun) | "diagram" / "summary" / "narration" — the specific format | Game team: "scene diagram" / "system summary." Always concrete. |
| `substrate` | "context" or "session data" | Claude Code's "# Context management" register. |
| `procedure` | "procedure" — keep the word; it is in Claude Code's register | Used in Claude Code's prompt (e.g. "# Committing changes with git" follows a procedure). |
| `judgment seam` | "when X, choose Y" / "if X, do Z" | The mechanism is named in plain conditional bullets, not as "judgment seam." |
| `change_response` | (internal — never appears in overlay) | Sync mode is internal to the skill. |
| `host_anchor` | (internal — never appears in overlay) | Anchor location is the skill's concern, not the overlay reader's. |
| `slot` | (internal — never appears in overlay) | The user reads sections; "slot" is the skill's word for them. |
| `subprotocol_principle` | (internal — never appears in overlay) | Principles get rendered as concrete bullets, never named. |
| `output_template` | (internal — never appears in overlay) | Templates are skill-side; the user reads the rendered output. |

## Idiom mapping

Beyond word-level substitution, certain Claude Code idioms must be respected for the overlay to read as Claude Code's own prompt rather than a foreign body.

- **`IMPORTANT:` prefix** for load-bearing rules. Use sparingly — Claude Code's own prompt uses it ~8 times across 600+ lines.
- **Imperative bullets**, not declarative prose. "Walk `definitions/` before generating." not "The agent should walk the definitions directory before generating."
- **`file_path:line_number`** as the citation form. Never `[file:line]`, never `path#L42` outside markdown link syntax.
- **NEVER / MUST / ALWAYS** modal verbs are reserved for the very loadest rules. Most rules are imperative without modal.
- **Heading hierarchy** matches Claude Code's: h1 for top-level (`# Doing tasks`), h2 for sub-rules (`## Source-first task discipline`), h3 sparingly. The overlay uses h2 for its slot sections to nest cleanly under whatever h1 the user's `CLAUDE.md` provides.
- **Code-block citations** use bash or markdown fences when showing path patterns or example forms.
- **End-of-turn summary** discipline: Claude Code's prompt instructs "one or two sentences. What changed and what's next." Overlay rules about citation should respect this terseness.

## When a SubProtocol term has no Claude Code equivalent

Two cases:

1. **The term is internal scaffolding** (`change_response`, `host_anchor`, `slot`, `output_template`). It does not appear in the overlay; it stays in the skill's machinery.
2. **The term names a behavior Claude Code does not natively have** (`source-first request resolution`, `realtime pointers`). Render the behavior as a concrete bullet in Claude Code's register; do not introduce the SubProtocol name.

Example:
- ❌ Overlay text: "Apply the source-first request resolution principle before any generation."
- ✅ Overlay text: "Before generating, walk `definitions/` for an existing module matching the task; prefer `file_path:line_number` to copy."

The principle is the same. The user reads concrete behavior in Claude Code's voice.

## Maintenance

When `system-prompt-shape` adds a new slot or renames a SubProtocol concept, update this table. When a Claude Code release changes its register (new top-level sections, new modal conventions, new citation form), update the **Idiom mapping** section. The map is read by `sync.py` at every run; out-of-date entries lead to overlay text in the wrong register.
