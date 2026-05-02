"""Walks the repo (skills/**/*.py and *.md) and emits one regime
classification data point per file. Classification is rule-based on
observable signals (top-level constants, import roots, file location);
fuzzy cases are emitted as regime=unclassified rather than guessed."""
from __future__ import annotations

from pathlib import Path

from ..lib import data_point as dp
from ..lib import source_features as sf

COLLECTOR_ID = "regime_classification"
KIND = "regime_classification"
VALUE_SCHEMA = {
    "type": "object",
    "required": ["path", "regime", "kind", "signals"],
}
INPUTS = ["skills/**/*.py", "**/*.md", "foundations/llm-sdk-denylist.txt"]
REPO_ROOT = sf.REPO_ROOT


def _signals(path: Path, denylist: frozenset[str]) -> list[str]:
    parts = path.relative_to(REPO_ROOT).parts
    out: list[str] = []
    tree = sf.parse(path)
    if tree is None:
        return ["parse_error"]
    consts = sf.top_level_consts(tree)
    for c in ("COLLECTOR_ID", "RESOLVER_ID", "SIGNAL_ID"):
        if c in consts:
            out.append(f"has_{c}")
    if "make_data_point" in sf.call_names(tree):
        out.append("calls_make_data_point")
    if sf.import_roots(tree) & denylist:
        out.append("imports_llm_sdk")
    if "lib" in parts:
        out.append("in_lib_dir")
    if "scripts" in parts:
        out.append("in_scripts_dir")
    if path.name == "orchestrate.py":
        out.append("is_orchestrate")
    if path.name == "verify.py":
        out.append("is_verify")
    if path.name == "render.py":
        out.append("is_render")
    return out


def _classify_python(path: Path, denylist: frozenset[str]) -> tuple[str, str, list[str]]:
    signals = _signals(path, denylist)
    if "parse_error" in signals:
        return "unclassified", "unparseable", signals
    if "imports_llm_sdk" in signals:
        return "0.3", "llm_using", signals
    if "is_orchestrate" in signals:
        return "0.3", "orchestration", signals
    if "is_verify" in signals:
        return "0.3", "verification", signals
    if "is_render" in signals:
        return "0.1", "renderer", signals
    if "has_SIGNAL_ID" in signals:
        return "0.2", "signal", signals
    if "has_RESOLVER_ID" in signals:
        return "0.1", "resolver", signals
    if "has_COLLECTOR_ID" in signals or "calls_make_data_point" in signals:
        return "0.1", "collector", signals
    if "in_lib_dir" in signals:
        return "0.1", "infrastructure", signals
    if "in_scripts_dir" in signals:
        return "0.1", "script", signals
    if path.name == "__init__.py":
        return "0.1", "package_marker", signals
    return "unclassified", "unknown_python", signals


def _classify_markdown(path: Path) -> tuple[str, str, list[str]]:
    parts = path.relative_to(REPO_ROOT).parts
    if parts and parts[0] == "foundations":
        return "bedrock", "foundation_spec", ["in_foundations_dir"]
    if path.name == "CLAUDE.md":
        return "0.0", "harness_root", ["is_claude_md"]
    if path.name == "SKILL.md":
        return "0.0", "skill_doc", ["is_skill_md"]
    if parts and parts[0] in ("meeting-notes", "debts"):
        return "0.0", "operator_note", [f"in_{parts[0]}_dir"]
    if "skills" in parts:
        return "0.0", "skill_doc", ["in_skill_subdir"]
    return "0.0", "prose", []


def compute_source_state() -> str:
    return sf.hash_file_corpus(sf.walk_targets())


def _collector_pointer() -> dict:
    return {"kind": "collector", "target": {"collector_id": COLLECTOR_ID},
            "resolver": "collector_resolver",
            "bound_at": {"source_state": None, "resolved_at": None},
            "last_status": "unresolved", "last_payload": None, "last_reason": None}


def collect(source_state: str) -> list[dict]:
    denylist = sf.read_denylist()
    cp = _collector_pointer()
    out: list[dict] = []
    for p in sf.walk_targets():
        rel = p.relative_to(REPO_ROOT).as_posix()
        if p.suffix == ".py":
            regime, kind, signals = _classify_python(p, denylist)
        else:
            regime, kind, signals = _classify_markdown(p)
        out.append(dp.make_data_point(
            collector_id=COLLECTOR_ID, kind=KIND,
            value={"path": rel, "regime": regime, "kind": kind, "signals": sorted(signals)},
            source_state=source_state, collector_pointer=cp,
        ))
    return out


def verify(data_point: dict) -> tuple[str, str]:
    rel = data_point["value"]["path"]
    return ("live", "present") if (REPO_ROOT / rel).exists() else ("dangling", "source_missing")
