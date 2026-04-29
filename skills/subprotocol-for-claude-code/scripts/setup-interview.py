"""setup-interview.py — first-time setup for subprotocol-for-claude-code.

Inspects the project root, gathers facts, and writes a starter
`references/domain-configuration.yaml` with reasonable defaults the user (or
the LLM running this skill) can refine. Also installs the SubProtocol overlay
markers in CLAUDE.md if they are not already there.

The "interview" half — proposing kinds, picking risk classes, confirming the
registry path — is handled by the LLM reading this skill (Claude Code itself,
when invoked as `subprotocol-for-claude-code setup`). This script does the
mechanical part: detect, default, and write.

Run from the project root, or pass --project <path>.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("subprotocol-for-claude-code/setup-interview.py requires PyYAML: pip install pyyaml")


CANDIDATE_REGISTRY_DIRS = ["definitions", "registry", "lore", "schemas", "kinds", "specs"]
CANDIDATE_SOURCE_DIRS = ["src", "lib", "app", "source", "code"]
CANDIDATE_TEST_DIRS = ["tests", "test", "spec", "specs"]


def detect_directories(project: Path) -> dict:
    """Detect probable layout of registry, source, and tests."""
    found = {"registry": None, "source": None, "tests": None}
    for name in CANDIDATE_REGISTRY_DIRS:
        if (project / name).is_dir():
            found["registry"] = f"{name}/"
            break
    for name in CANDIDATE_SOURCE_DIRS:
        if (project / name).is_dir():
            found["source"] = f"{name}/"
            break
    for name in CANDIDATE_TEST_DIRS:
        if (project / name).is_dir():
            found["tests"] = f"{name}/"
            break
    return found


def detect_existing_claude_md(project: Path) -> dict:
    """Read CLAUDE.md if present; report markers status and rough size."""
    claude_md = project / "CLAUDE.md"
    if not claude_md.exists():
        return {"exists": False}
    text = claude_md.read_text(encoding="utf-8")
    return {
        "exists": True,
        "size_bytes": len(text.encode("utf-8")),
        "lines": len(text.splitlines()),
        "has_start_marker": "<!-- SUBPROTOCOL:OVERLAY:START" in text,
        "has_end_marker": "<!-- SUBPROTOCOL:OVERLAY:END -->" in text,
    }


def propose_config(project: Path, dirs: dict) -> dict:
    """Build a starter domain-configuration.yaml structure with defaults."""
    project_name = project.resolve().name
    registry = dirs["registry"] or "definitions/"
    source_root = dirs["source"] or "src/"
    tests_root = dirs["tests"] or "tests/"

    cfg = {
        "project": {
            "name": project_name,
            "domain": "(set me — short slug, e.g. 'game-dev', 'legal-review')",
            "customization_filename": "CLAUDE.md",
        },
        "slots": {
            "engineering-task-discipline": {
                "enabled": True,
                "fills": {
                    "registry_path": registry,
                    "asset_kinds": ["(set me — list your domain nouns)"],
                    "pointer_format": "file_path:line_number",
                    "source_layout": {
                        "source_root": source_root,
                        "definitions_root": registry,
                        "tests_root": tests_root,
                    },
                },
            },
            "tool-use-discipline": {
                "enabled": True,
                "fills": {
                    "subprotocol_tools": [
                        {
                            "name": "definition_lookup",
                            "purpose": "search the registry for an existing definition matching the task",
                        },
                    ],
                    "parallel_invocation_examples": [],
                },
            },
            "autonomy-and-action-discipline": {
                "enabled": True,
                "fills": {
                    "risk_classes": ["(set me — what counts as risky in this project)"],
                    "confirm_threshold": "named-risk-classes",
                    "source_walk_first": True,
                },
            },
            "git-rules": {
                "enabled": True,
                "fills": {
                    "commit_message_template": "{verb} {asset_kind}: {summary}\n\nReferences: {pointer_format}",
                    "pr_evidence_path": "evidence/",
                },
            },
            "formatting-and-output-style": {
                "enabled": True,
                "fills": {
                    "citation_format": "file_path:line_number",
                    "end_of_turn_summary_includes_asset_kind": True,
                },
            },
            "host-templated-data-runtime": {
                "enabled": False,  # opt in once registry is populated
                "fills": {
                    "injection_keys": ["subprotocol_registry_summary"],
                    "subprotocol_substrate": {
                        "registry_summary": {"recent_definitions_n": 5},
                    },
                },
            },
            "memory-subsystem": {
                "enabled": True,
                "fills": {
                    "subprotocol_memory_kinds": ["definition-derivation-history", "task-resolution-trace"],
                    "memory_save_template": "Saved as `file_path:line_number` reference, not paraphrase.",
                },
            },
            "planning-procedure": {
                "enabled": False,  # opt in if your team uses formal planning artifacts
                "fills": {
                    "plan_template": "1. Walk {registry_path} for matching definition.\n2. ...",
                    "pre_act_check": ["registry walk completed", "no existing match found"],
                },
            },
            "procedure": {
                "enabled": False,  # opt in once procedures are named
                "fills": {
                    "procedure_kinds": [],
                },
            },
            "render": {
                "enabled": False,  # opt in once render targets are decided
                "fills": {
                    "render_kinds": [],
                },
            },
        },
    }
    return cfg


def write_config(skill_dir: Path, cfg: dict, force: bool) -> Path:
    config_path = skill_dir / "references" / "domain-configuration.yaml"
    if config_path.exists() and not force:
        sys.exit(f"{config_path} already exists; pass --force to overwrite")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return config_path


def install_markers(claude_md: Path) -> bool:
    """Append the marker pair to CLAUDE.md if not present. Returns True if changed."""
    start = "<!-- SUBPROTOCOL:OVERLAY:START — generated, do not edit between markers -->"
    end = "<!-- SUBPROTOCOL:OVERLAY:END -->"
    if not claude_md.exists():
        claude_md.write_text(
            f"# {claude_md.parent.name}\n\n{start}\n(overlay will be generated by sync.py)\n{end}\n",
            encoding="utf-8",
        )
        return True
    text = claude_md.read_text(encoding="utf-8")
    if start in text and end in text:
        return False
    sep = "" if text.endswith("\n") else "\n"
    text += sep + "\n" + start + "\n(overlay will be generated by sync.py)\n" + end + "\n"
    claude_md.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="First-time setup for subprotocol-for-claude-code")
    parser.add_argument("--project", default=".", help="project root (default: cwd)")
    parser.add_argument("--force", action="store_true", help="overwrite existing domain-configuration.yaml")
    parser.add_argument("--no-install-markers", action="store_true", help="do not modify CLAUDE.md")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    skill_dir = Path(__file__).resolve().parent.parent

    print(f"setup-interview: scanning {project}")
    dirs = detect_directories(project)
    print(f"  detected registry: {dirs['registry'] or '(none — defaulting to definitions/)'}")
    print(f"  detected source:   {dirs['source'] or '(none — defaulting to src/)'}")
    print(f"  detected tests:    {dirs['tests'] or '(none — defaulting to tests/)'}")

    claude_status = detect_existing_claude_md(project)
    if claude_status["exists"]:
        print(f"  CLAUDE.md exists ({claude_status['size_bytes']} bytes, {claude_status['lines']} lines)")
        if claude_status["has_start_marker"] and claude_status["has_end_marker"]:
            print("  overlay markers already present")
        else:
            print("  overlay markers missing")
    else:
        print("  CLAUDE.md not found — will create one")

    cfg = propose_config(project, dirs)
    config_path = write_config(skill_dir, cfg, args.force)
    print(f"  wrote starter config: {config_path}")

    if not args.no_install_markers:
        changed = install_markers(project / "CLAUDE.md")
        if changed:
            print(f"  installed overlay markers in {project / 'CLAUDE.md'}")

    print()
    print("Next steps:")
    print(f"  1. Open {config_path} and replace the `(set me — ...)` placeholders.")
    print("     Required: project.domain, asset_kinds, risk_classes.")
    print("  2. Optionally enable: host-templated-data-runtime, planning-procedure, procedure, render.")
    print("  3. Run sync.py to generate the overlay:")
    print("       python scripts/sync.py")
    print("  4. Inspect CLAUDE.md to confirm the overlay region looks right in Claude Code's register.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
