"""Receipt manifest helpers shared by leash orchestrators."""
from __future__ import annotations

from pathlib import Path


def validation_receipts(skill_root: Path, collector_summary: dict, signals: tuple) -> dict:
    repo_root = skill_root.parents[1]
    return {
        "bundle_walker": "verify.py",
        "collector_receipts": {
            cid: {
                "dataset": meta["dataset_path"],
                "source_state": f"datasets/{cid}.source_state",
            }
            for cid, meta in sorted(collector_summary.items())
        },
        "signal_probe_runners": {
            mod.SIGNAL_ID: str(Path(mod.__file__).resolve().relative_to(repo_root)).replace("\\", "/")
            for mod in signals
        },
    }
