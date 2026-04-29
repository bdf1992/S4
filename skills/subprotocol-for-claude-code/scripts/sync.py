"""sync.py — regenerate the SubProtocol overlay region in CLAUDE.md.

Reads `references/domain-configuration.yaml`, walks the slots that are
enabled and not change_response: block, renders each slot's output_template
with fills + Claude Code's translation map, composes the overlay body, and
writes it between the two literal-string markers in CLAUDE.md.

Operations (the first positional arg):

    sync      Default. Regenerate the overlay region from current source.
    check     Render expected overlay; diff against current; non-zero on drift.
    add-slot  <slot-name> — flip enabled=true on the named slot. Prompts for
              required fills if missing.

Run from the project root that contains CLAUDE.md, or pass --project <path>.

Requires PyYAML (pip install pyyaml). v0.1 is content-only; pre/post timing
slots are reserved on every slot but unused.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("subprotocol-for-claude-code/sync.py requires PyYAML: pip install pyyaml")


MARKER_START = "<!-- SUBPROTOCOL:OVERLAY:START — generated, do not edit between markers -->"
MARKER_END = "<!-- SUBPROTOCOL:OVERLAY:END -->"


# Corpus-derived per-category density floors (per 100 lines).
# Authoritative documentation: system-prompt-shape/references/section-taxonomy.md
# Source data: system-prompt-shape/reports/overlay-vs-corpus.md (pass 0 corpus survey).
DENSITY_FLOOR = {
    "imperatives_per_100ln": 8.4,   # Jules
    "never_per_100ln":       0.0,   # Jules
    "must_per_100ln":        2.3,   # CC
    "always_per_100ln":      0.88,  # Codex
    "do_not_per_100ln":      6.3,   # Gemini
    "tool_mentions_per_100ln": 0.0, # Codex
    "bullets_per_100ln":     34.8,  # CC
}


def _normalize_for_diff(text: str) -> str:
    """Strip lines that legitimately change every run (timestamp) before diffing."""
    return "\n".join(
        line for line in text.splitlines()
        if not line.startswith("**Generated:**")
    )


def _compute_density(text: str) -> dict:
    """Compute per-100ln densities for each tracked category."""
    lines = max(1, len(text.splitlines()))
    scale = 100.0 / lines
    return {
        "imperatives_per_100ln": _count_imperatives(text) * scale,
        "never_per_100ln":       len(re.findall(r"\bnever\b", text, re.IGNORECASE)) * scale,
        "must_per_100ln":        len(re.findall(r"\bmust\b",  text, re.IGNORECASE)) * scale,
        "always_per_100ln":      len(re.findall(r"\balways\b",text, re.IGNORECASE)) * scale,
        "do_not_per_100ln":      len(re.findall(r"\b(do not|don't)\b", text, re.IGNORECASE)) * scale,
        "tool_mentions_per_100ln": _count_tool_mentions(text) * scale,
        "bullets_per_100ln":     sum(1 for ln in text.splitlines() if re.match(r"\s*[-*]\s+", ln)) * scale,
        "lines": len(text.splitlines()),
    }


_TOOLS_FOR_DENSITY = {
    "Read", "Edit", "Write", "Bash", "Grep", "Glob", "Agent", "Skill",
    "TodoWrite", "WebFetch", "WebSearch", "Monitor", "ScheduleWakeup",
    "PowerShell", "ToolSearch", "definition_lookup", "scene_graph_compute",
}


def _count_tool_mentions(text: str) -> int:
    return sum(len(re.findall(rf"\b{re.escape(t)}\b", text)) for t in _TOOLS_FOR_DENSITY)


_DENSITY_STOPWORDS = {
    "The", "A", "An", "This", "That", "These", "Those", "There", "Here",
    "It", "Its", "You", "Your", "We", "Our", "My", "His", "Her", "Their",
    "In", "On", "At", "By", "For", "With", "From", "Of", "To", "And", "Or",
    "But", "If", "When", "While", "Because", "Since", "Now", "Then", "So",
    "As", "Like", "Note", "Notes", "Example", "Examples", "Important",
    "Trigger", "References", "Some", "Any", "All", "Each", "Every", "Both",
    "Per", "Most", "Many", "Several", "Few", "Generated", "Sample",
    "Provenance", "Active", "Source", "Project", "Will", "Would", "Should",
    "Could", "May", "Might", "Can", "Risk", "Tool", "Memory", "Schema",
    "Step", "Steps", "Procedure", "Procedures", "Slot", "Slots", "Judgment",
    "Stop", "Codex", "Gemini", "Claude", "Jules", "Anthropic", "Google",
    "OpenAI", "SubProtocol",
}

_DENSITY_PREFIX_RE = re.compile(
    r"^\s*(?:[-*]\s+|\d+\.\s+|\*\*[^*]+\*\*\s*:?\s*|IMPORTANT:\s*|NOTE:\s*)?"
)
_DENSITY_WORD_RE = re.compile(r"^([A-Za-z][A-Za-z']*)")


def _count_imperatives(text: str) -> int:
    n = 0
    for line in text.splitlines():
        stripped = _DENSITY_PREFIX_RE.sub("", line.rstrip())
        m = _DENSITY_WORD_RE.match(stripped)
        if not m:
            continue
        first = m.group(1)
        if (len(first) >= 2 and first[0].isupper() and first[1:].islower()
                and first not in _DENSITY_STOPWORDS):
            n += 1
    return n


def _format_density_report(density: dict, floor: dict) -> tuple[str, bool]:
    """Return (markdown_table, all_pass)."""
    rows = ["| category | overlay /100ln | floor /100ln | status |",
            "|---|---|---|---|"]
    all_pass = True
    for key, floor_val in floor.items():
        actual = density.get(key, 0.0)
        passed = actual >= floor_val
        if not passed:
            all_pass = False
        status = "OK" if passed else f"BELOW (gap {floor_val - actual:.2f})"
        rows.append(f"| {key} | {actual:.2f} | {floor_val:.2f} | {status} |")
    return "\n".join(rows), all_pass


# ---------------------------------------------------------------------------
# Translation map — SubProtocol-internal vocabulary → Claude Code register.
# Mirrors references/translation-map.md. Edit both together.
# ---------------------------------------------------------------------------

TRANSLATION_MAP = {
    "request": "task",
    "pointer": "file_path:line_number",
    "registry": None,  # use the user's registry_path directly
    "asset": None,     # use the user's asset_kinds directly
    "kind": None,      # use the user's specific kind name
    "substrate": "context",
    "register": "save under",
}


# ---------------------------------------------------------------------------
# Slot templates — mirrors section-taxonomy.md output_template + change_response.
# v0.1 keeps these as Python constants; v0.2 may derive from the markdown.
# ---------------------------------------------------------------------------

SLOTS = [
    # (slot_name, change_response, render_fn)
    # Order matches overlay.md composition order.
    ("repo-customization-protocol",        "regenerate", "render_slot_16"),
    ("engineering-task-discipline",        "regenerate", "render_slot_2"),
    ("tool-use-discipline",                "regenerate", "render_slot_3"),
    ("autonomy-and-action-discipline",     "regenerate", "render_slot_4"),
    ("git-rules",                          "regenerate", "render_slot_5"),
    ("formatting-and-output-style",        "regenerate", "render_slot_7"),
    ("host-templated-data-runtime",        "regenerate", "render_slot_8a"),
    ("tool-spec-catalog",                  "regenerate", "render_slot_9"),
    ("agent-tool-discipline",              "regenerate", "render_slot_10"),
    ("memory-subsystem",                   "regenerate", "render_slot_11"),
    ("planning-procedure",                 "regenerate", "render_slot_13"),
    ("context-management",                 "regenerate", "render_slot_14"),
    ("domain-task-aesthetic",              "regenerate", "render_slot_15"),
    ("request-routing-rules",              "regenerate", "render_slot_18"),
    ("procedure",                          "regenerate", "render_slot_20"),
    ("render",                             "regenerate", "render_slot_21"),
]

NOOP_SLOTS = {"persona", "global-safety-and-refusal", "session-and-help-meta"}


# ---------------------------------------------------------------------------
# Per-slot render functions. Each takes the slot's `fills` dict and the
# project-wide context, returns the markdown body for that slot (or "" to skip).
# Bodies are in Claude Code's register — never SubProtocol-internal vocabulary.
# ---------------------------------------------------------------------------

def render_slot_16(fills, ctx):
    return ""  # structural — declared in header, no body


def render_slot_2(fills, ctx):
    registry = fills["registry_path"]
    kinds = fills["asset_kinds"]
    kind_list = ", ".join(f"`{k}`" for k in kinds)
    primary = kinds[0]
    return f"""## Source-first task discipline

- Walk `{registry}` BEFORE generating new code. If a `file_path:line_number` matches the task, return the pointer and stop — do not generate a duplicate.
- Save new {primary}s under `{registry}<kind>/` (kinds: {kind_list}). Don't bypass the registry; subsequent tasks resolve via search.
- Don't paraphrase definitions in responses — cite by `file_path:line_number` from current state.
- IMPORTANT: source-walk happens BEFORE the first edit, not after."""


def render_slot_3(fills, ctx):
    tools = fills.get("subprotocol_tools", [])
    if not tools:
        return ""
    bullets = "\n".join(
        f"- Before generating, invoke `{t['name']}` against `{ctx['registry_path']}`; if it resolves, return the `file_path:line_number` instead of generating."
        for t in tools
    )
    return f"""## Tool-use discipline (SubProtocol additions)

- MUST source-walk `{ctx['registry_path']}` before invoking any generation tool — the SubProtocol tools below are how that walk happens.
{bullets}
- When invoking these tools, parallelize where independent — same parallelism rule as Claude Code's existing tool-use discipline.
- Do not chain SubProtocol tool calls behind a generation step; the source-walk runs first or it does not run at all."""


def render_slot_4(fills, ctx):
    risks = fills["risk_classes"]
    risk_list = ", ".join(f"`{r}`" for r in risks)
    return f"""## Action discipline (source-walk before risk)

- Risk classes for this project: {risk_list}.
- IMPORTANT: ALWAYS source-walk `{ctx['registry_path']}` before any action in those classes. If a `file_path:line_number` resolves the task, prefer that path.
- MUST report source-walk results back as `file_path:line_number`, not as paraphrase, so the user can verify against current state.
- If source-walk yields no resolution, defer to Claude Code's existing confirmation discipline (the `# Executing actions with care` rules).
- Do not bypass the source-walk for speed — destructive operations against unwalked state is the failure mode this slot exists to prevent."""


def render_slot_5(fills, ctx):
    template = fills["commit_message_template"].replace("\n", " · ")
    evidence = fills["pr_evidence_path"]
    primary = ctx["asset_kinds"][0]
    return f"""## Commit and PR rules (SubProtocol additions)

- NEVER paraphrase what changed in a commit message — cite by `file_path:line_number` from current state.
- Do not hand-edit the SubProtocol overlay region in CLAUDE.md; it is regenerated and your edits will be clobbered. Edit `domain-configuration.yaml` instead.
- PR descriptions link to evidence at `{evidence}`; the diff impact is computed there, the message points at it.
- Commit messages reference {primary}s by `file_path:line_number`, not by paraphrase. Template: `{template}`."""


def render_slot_7(fills, ctx):
    cite = fills.get("citation_format", "file_path:line_number")
    summary_kind = fills.get("end_of_turn_summary_includes_asset_kind", True)
    summary_rule = (
        f"- End-of-turn summary names the {ctx['asset_kinds'][0]} when relevant."
        if summary_kind else ""
    )
    return f"""## Formatting (SubProtocol additions)

- NEVER paraphrase source — cite by `{cite}` from current state, not from memory.
{summary_rule}""".strip()


def render_slot_8a(fills, ctx):
    keys = fills.get("injection_keys", [])
    if not keys:
        return ""
    bullets = "\n".join(f"- `{k}` — published from `{ctx['registry_path']}` at session start." for k in keys)
    return f"""## Environment additions (SubProtocol substrate)

The following keys are populated from `{ctx['registry_path']}` when this prompt is built per-session:

{bullets}"""


def render_slot_9(fills, ctx):
    tools = fills.get("subprotocol_tool_specs", [])
    if not tools:
        return ""
    blocks = []
    for t in tools:
        blocks.append(f"""## {t['name']}

{t.get('purpose', '')}

```
{t.get('signature', '')}
```""")
    return "\n\n".join(blocks)


def render_slot_10(fills, ctx):
    return """## Subagent context (SubProtocol addition)

- When invoking the Agent tool, include the current registry summary in the subagent's prompt so its work resolves against the same source state."""


def render_slot_11(fills, ctx):
    kinds = fills.get("subprotocol_memory_kinds", [])
    if not kinds:
        return ""
    kind_list = ", ".join(f"`{k}`" for k in kinds)
    return f"""## Memory rules (SubProtocol additions)

These rules are SubProtocol contributions to Claude Code's existing memory subsystem (see `# auto memory` above). The subsystem itself is host-owned; SubProtocol adds discipline, not structure.

- ALWAYS save memories as `file_path:line_number` references from current state, not from session-derived paraphrase.
- MUST reverify on access — memory references rot; recompute from source rather than trusting stored notes.
- Do not save derived primitives (counts, summaries, drift metrics) — those are computed on demand, not noted.
- SubProtocol memory kinds: {kind_list}."""


def render_slot_13(fills, ctx):
    pre_acts = fills.get("pre_act_check", [])
    pre_block = "\n".join(f"  - {p}" for p in pre_acts) if pre_acts else "  - (none configured)"
    return f"""## Planning additions

- MUST start every plan with: walk `{ctx['registry_path']}` for an existing {ctx['asset_kinds'][0]} matching the task. The walk is plan step 1; it is not optional.
- Do not include a generation step until the walk has been recorded.
- Pre-act checks run before any generation step:
{pre_block}"""


def render_slot_14(fills, ctx):
    return f"""## Context management (SubProtocol additions)

- Context entries from `{ctx['registry_path']}` are recomputed per session; do not trust cached snapshots.
- When a turn references SubProtocol substrate that may have changed, recompute from source rather than re-using the prior turn's value."""


def render_slot_15(fills, ctx):
    registry = fills.get("design_asset_registry")
    if not registry:
        return ""
    return f"""## Domain-task aesthetic

- Before generating new design tokens, check `{registry}` for existing matches; prefer `file_path:line_number` to copy."""


def render_slot_18(fills, ctx):
    routing = fills.get("keyword_routing_map", {})
    if not routing:
        return ""
    bullets = "\n".join(
        f"- If the user uses `{kw}`, route through {flow} before any default action."
        for kw, flow in routing.items()
    )
    return f"""## Request-routing rules

{bullets}"""


def render_slot_20(fills, ctx):
    procs = fills.get("procedure_kinds", [])
    if not procs:
        return ""
    blocks = []
    for proc in procs:
        steps = "\n".join(f"{i+1}. {s['body']}" for i, s in enumerate(proc.get("steps", [])))
        seams = ""
        if proc.get("judgment_seams"):
            seam_lines = []
            for s in proc["judgment_seams"]:
                opts = "; or ".join(f"({chr(97+i)}) {opt}" for i, opt in enumerate(s["options"]))
                seam_lines.append(
                    f"- Judgment ({s['seam_name']}): when {s['condition']}, choose between {opts}. Name the chosen option in the response before continuing."
                )
            seams = "\n\n" + "\n".join(seam_lines)
        exits = ""
        if proc.get("exit_conditions"):
            exit_lines = "\n".join(f"- Stop early if {c}." for c in proc["exit_conditions"])
            exits = f"\n\n{exit_lines}"
        blocks.append(
            f"""### Procedure: {proc['name']}

Trigger: {proc.get('trigger', '(unspecified)')}

{steps}{seams}{exits}"""
        )
    return ("## Procedures\n\n"
            "Run procedure steps in order. NEVER skip a step without naming the exit condition that justifies it.\n\n"
            + "\n\n".join(blocks))


def render_slot_21(fills, ctx):
    renders = fills.get("render_kinds", [])
    if not renders:
        return ""
    bullets = []
    for r in renders:
        bullets.append(
            f"- When {r['trigger']}, compute `{r['name']}` from `{ctx['registry_path']}` and emit as {r['format']} to `{r['path']}`."
        )
    bullets.append(
        "- NEVER hand-edit a render file — they are regenerated; edits will be clobbered and stale renders fail validation."
    )
    bullets.append(
        "- When citing a render in a message, use `file_path:line_number` to the render path, not a paraphrase of its contents."
    )
    return "## Computed renders\n\n" + "\n".join(bullets)


RENDERERS = {
    "render_slot_16":  render_slot_16,
    "render_slot_2":   render_slot_2,
    "render_slot_3":   render_slot_3,
    "render_slot_4":   render_slot_4,
    "render_slot_5":   render_slot_5,
    "render_slot_7":   render_slot_7,
    "render_slot_8a":  render_slot_8a,
    "render_slot_9":   render_slot_9,
    "render_slot_10":  render_slot_10,
    "render_slot_11":  render_slot_11,
    "render_slot_13":  render_slot_13,
    "render_slot_14":  render_slot_14,
    "render_slot_15":  render_slot_15,
    "render_slot_18":  render_slot_18,
    "render_slot_20":  render_slot_20,
    "render_slot_21":  render_slot_21,
}


# ---------------------------------------------------------------------------
# Config loading + validation.
# ---------------------------------------------------------------------------

def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        sys.exit(f"domain-configuration.yaml not found at {config_path}. Run setup-interview.py first.")
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def validate_config(cfg: dict) -> list[str]:
    errors: list[str] = []
    if "project" not in cfg:
        errors.append("missing top-level `project` block")
    else:
        for k in ("name", "domain"):
            if k not in cfg["project"]:
                errors.append(f"missing project.{k}")
    if "slots" not in cfg or not isinstance(cfg["slots"], dict):
        errors.append("missing or malformed `slots` block")
    else:
        known = {s[0] for s in SLOTS} | NOOP_SLOTS
        for slot_name in cfg["slots"]:
            if slot_name not in known:
                errors.append(f"unknown slot: {slot_name}")
    return errors


def collect_ctx(cfg: dict) -> dict:
    eng = cfg.get("slots", {}).get("engineering-task-discipline", {}).get("fills", {})
    return {
        "registry_path": eng.get("registry_path", "definitions/"),
        "asset_kinds": eng.get("asset_kinds", ["module"]),
        "pointer_format": eng.get("pointer_format", "file_path:line_number"),
    }


# ---------------------------------------------------------------------------
# Composition + write.
# ---------------------------------------------------------------------------

def compose_overlay(cfg: dict, ctx: dict) -> str:
    project = cfg["project"]
    timestamp = _dt.datetime.now().isoformat(timespec="seconds")
    slots_cfg = cfg.get("slots", {})
    enabled_count = sum(1 for s in SLOTS if slots_cfg.get(s[0], {}).get("enabled"))

    parts: list[str] = []
    parts.append(f"""# SubProtocol overlay — Claude Code

**Generated:** {timestamp} by `subprotocol-for-claude-code/scripts/sync.py`
**Source of truth:** `{cfg.get('_config_relpath', 'references/domain-configuration.yaml')}` (do not edit this region directly; edit the configuration and re-run `sync`)
**Project:** {project['name']} (domain: {project['domain']})
**Active slots:** {enabled_count} of {len(SLOTS)} non-NOOP

The rules below ride under Claude Code's existing prompt. They never override Claude Code's own discipline; they add SubProtocol behavior in Claude Code's register.""")

    for slot_name, change_response, render_key in SLOTS:
        slot_cfg = slots_cfg.get(slot_name, {})
        if not slot_cfg.get("enabled"):
            continue
        effective_response = slot_cfg.get("change_response", change_response)
        if effective_response == "block":
            continue
        if effective_response == "collect":
            continue  # data goes to record, no overlay body
        body = RENDERERS[render_key](slot_cfg.get("fills", {}), ctx)
        if body.strip():
            parts.append(body)

    parts.append("""---
**Provenance:** every rule above traces to a slot in `system-prompt-shape/references/section-taxonomy.md`, filled by `domain-configuration.yaml`. Run `sync.py check` to verify drift; run `sync.py sync` to regenerate.""")

    return "\n\n".join(parts)


def write_overlay(claude_md: Path, overlay_body: str) -> tuple[bool, str]:
    """Write overlay between markers in claude_md. Returns (changed, old_overlay)."""
    if not claude_md.exists():
        claude_md.write_text(
            f"# {claude_md.parent.name}\n\n{MARKER_START}\n{overlay_body}\n{MARKER_END}\n",
            encoding="utf-8",
        )
        return True, ""
    text = claude_md.read_text(encoding="utf-8")
    new_block = f"{MARKER_START}\n{overlay_body}\n{MARKER_END}"
    if MARKER_START in text and MARKER_END in text:
        start = text.index(MARKER_START)
        end = text.index(MARKER_END) + len(MARKER_END)
        old_overlay = text[start + len(MARKER_START): text.index(MARKER_END)].strip()
        new_text = text[:start] + new_block + text[end:]
    else:
        old_overlay = ""
        sep = "" if text.endswith("\n") else "\n"
        new_text = text + sep + "\n" + new_block + "\n"
    if new_text != text:
        claude_md.write_text(new_text, encoding="utf-8")
        return True, old_overlay
    return False, old_overlay


def write_record(record_dir: Path, cfg: dict, changed: bool, drift: str) -> Path:
    record_dir.mkdir(parents=True, exist_ok=True)
    today = _dt.date.today().isoformat()
    record = record_dir / f"sync-{today}.md"
    slots_cfg = cfg.get("slots", {})
    enabled = [s for s, _, _ in SLOTS if slots_cfg.get(s, {}).get("enabled")]
    lines = [
        f"# Sync record — {today}",
        "",
        f"**Project:** {cfg['project']['name']}",
        f"**Changed:** {changed}",
        f"**Active slots:** {', '.join(enabled) if enabled else '(none)'}",
        "",
        "## Drift" if drift else "## No drift detected",
    ]
    if drift:
        lines.append("```diff")
        lines.append(drift)
        lines.append("```")
    record.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return record


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="SubProtocol overlay sync for Claude Code")
    parser.add_argument("operation", nargs="?", default="sync",
                        choices=["sync", "check", "add-slot", "check-density"])
    parser.add_argument("slot", nargs="?", default=None, help="slot name when operation is add-slot")
    parser.add_argument("--project", default=".", help="project root containing CLAUDE.md (default: cwd)")
    parser.add_argument("--config", default=None, help="path to domain-configuration.yaml")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    skill_dir = Path(__file__).resolve().parent.parent
    config_path = Path(args.config).resolve() if args.config else skill_dir / "references" / "domain-configuration.yaml"
    claude_md = project / "CLAUDE.md"

    cfg = load_config(config_path)
    cfg["_config_relpath"] = str(config_path.relative_to(project)) if config_path.is_relative_to(project) else str(config_path)
    errors = validate_config(cfg)
    if errors:
        print("Configuration errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2

    ctx = collect_ctx(cfg)
    overlay_body = compose_overlay(cfg, ctx)

    if args.operation == "sync":
        changed, old = write_overlay(claude_md, overlay_body)
        drift = ""
        old_n = _normalize_for_diff(old)
        new_n = _normalize_for_diff(overlay_body.strip())
        if old and old_n != new_n:
            drift = "\n".join(difflib.unified_diff(
                old_n.splitlines(), new_n.splitlines(),
                fromfile="before", tofile="after", lineterm=""
            ))
        record = write_record(skill_dir / "reports", cfg, changed, drift)
        print(f"sync: {'changed' if changed else 'no change'} in {claude_md}")
        print(f"record: {record}")

        density = _compute_density(overlay_body)
        report, all_pass = _format_density_report(density, DENSITY_FLOOR)
        if not all_pass:
            print("\ndensity: BELOW corpus floor — overlay reads soft. See:", file=sys.stderr)
            print(report, file=sys.stderr)
            return 1
        return 0

    if args.operation == "check":
        if not claude_md.exists():
            print("CLAUDE.md missing", file=sys.stderr)
            return 1
        text = claude_md.read_text(encoding="utf-8")
        if MARKER_START not in text or MARKER_END not in text:
            print("overlay markers missing — run sync to install", file=sys.stderr)
            return 1
        old = text[text.index(MARKER_START) + len(MARKER_START):text.index(MARKER_END)].strip()
        if _normalize_for_diff(old) == _normalize_for_diff(overlay_body.strip()):
            print("no drift")
            return 0
        diff = "\n".join(difflib.unified_diff(
            _normalize_for_diff(old).splitlines(),
            _normalize_for_diff(overlay_body.strip()).splitlines(),
            fromfile="overlay (current)", tofile="overlay (expected)", lineterm=""
        ))
        print(diff)
        return 1

    if args.operation == "check-density":
        density = _compute_density(overlay_body)
        report, all_pass = _format_density_report(density, DENSITY_FLOOR)
        print(f"Overlay lines: {density['lines']}")
        print(report)
        if all_pass:
            print("\ndensity: all categories at or above corpus floor")
            return 0
        print("\ndensity: BELOW corpus floor on one or more categories — overlay reads soft", file=sys.stderr)
        return 1

    if args.operation == "add-slot":
        if not args.slot:
            print("add-slot requires a slot name", file=sys.stderr)
            return 2
        known = {s[0] for s in SLOTS}
        if args.slot not in known:
            print(f"unknown slot: {args.slot}. known: {sorted(known)}", file=sys.stderr)
            return 2
        slots_cfg = cfg.setdefault("slots", {})
        slot_cfg = slots_cfg.setdefault(args.slot, {})
        slot_cfg["enabled"] = True
        slot_cfg.setdefault("fills", {})
        config_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        print(f"enabled slot: {args.slot} in {config_path}")
        print("Edit `fills:` for this slot, then run `sync` to regenerate the overlay.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
