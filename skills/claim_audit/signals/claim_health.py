"""0.2 signal — claim_health.

Question answered: across the markdown_claims dataset, what fraction of
internal (repo-pointing) claims resolve `live`? Which source files carry
the most dangling claims? What share of internal claims are
section-anchored (currently unverified by construction — the punt)?

Fitting: walks the training dataset and computes aggregate counts. The
fitted parameter is a stats dict; re-fitting is deterministic.

Probe set: synthetic datasets with known expected counts; verify.py runs
the probes against the signal to confirm fit-time behavior holds at
verification time.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

SIGNAL_ID = "claim_health"
TRAINING_DATASET_KIND = "md_link"
VERDICT_ENUM = ("healthy", "degraded", "no_data")

RECEIPTS = ("live", "dangling_file", "dangling_line", "external",
            "anchor_unverified")
INTERNAL_RECEIPTS = ("live", "dangling_file", "dangling_line",
                     "anchor_unverified")
DANGLING_RECEIPTS = ("dangling_file", "dangling_line")

DEGRADED_THRESHOLD = 0.95  # internal live_ratio below this = degraded


def fit(training_rows: list[dict]) -> dict:
    by_receipt: Counter = Counter()
    by_target_kind: Counter = Counter()
    by_source: dict[str, Counter] = {}
    total = 0
    internal = 0
    for r in training_rows:
        v = r.get("value", {})
        receipt = v.get("receipt", "unknown")
        target_kind = v.get("target_kind", "unknown")
        source = v.get("source", "")
        by_receipt[receipt] += 1
        by_target_kind[target_kind] += 1
        by_source.setdefault(source, Counter())[receipt] += 1
        total += 1
        if receipt in INTERNAL_RECEIPTS:
            internal += 1
    live = by_receipt.get("live", 0)
    dangling = sum(by_receipt.get(r, 0) for r in DANGLING_RECEIPTS)
    unverified = by_receipt.get("anchor_unverified", 0)
    live_ratio = (live / internal) if internal > 0 else None
    dangling_ratio = (dangling / internal) if internal > 0 else None
    unverified_ratio = (unverified / internal) if internal > 0 else None
    return {
        "total": total,
        "internal": internal,
        "live": live,
        "dangling": dangling,
        "unverified_anchor": unverified,
        "external": by_receipt.get("external", 0),
        "by_receipt": dict(by_receipt),
        "by_target_kind": dict(by_target_kind),
        "by_source": {k: dict(c) for k, c in by_source.items()},
        "live_ratio": live_ratio,
        "dangling_ratio": dangling_ratio,
        "unverified_ratio": unverified_ratio,
    }


def _verdict(fitted: dict) -> str:
    if fitted["total"] == 0:
        return "no_data"
    lr = fitted["live_ratio"]
    if lr is None or lr >= DEGRADED_THRESHOLD:
        return "healthy"
    return "degraded"


def evaluate(query: dict, *, fitted: dict, training_rows: list[dict]) -> dict:
    verdict = _verdict(fitted)
    if verdict == "no_data":
        return {"verdict": "no_data", "stats": fitted, "matching_count": 0,
                "evidence_pointers": []}
    matched: list[dict] = []
    for r in training_rows:
        v = r.get("value", {})
        if "receipt" in query and v.get("receipt") != query["receipt"]:
            continue
        if "target_kind" in query and v.get("target_kind") != query["target_kind"]:
            continue
        if "source" in query and v.get("source") != query["source"]:
            continue
        matched.append(r)
    evidence = [{"kind": "data_point", "target": {"dp_id": r["id"]},
                 "resolver": "data_point_resolver"} for r in matched[:10]]
    return {"verdict": verdict, "stats": fitted,
            "matching_count": len(matched),
            "matching_rows": [{"source": m["value"]["source"],
                               "line": m["value"]["line"],
                               "target_raw": m["value"]["target_raw"],
                               "receipt": m["value"]["receipt"]}
                              for m in matched],
            "evidence_pointers": evidence}


def _row(source: str, line: int, target_raw: str, target_kind: str, receipt: str) -> dict:
    return {"id": f"markdown_claims:probe-{source}-{line}",
            "value": {"source": source, "line": line, "target_raw": target_raw,
                      "target_kind": target_kind, "receipt": receipt}}


PROBES: list[dict] = [
    {
        "name": "all_live",
        "training": [
            _row("CLAUDE.md", 1, "foundations/data-point.md", "repo_path", "live"),
            _row("CLAUDE.md", 2, "skills/x/", "repo_path", "live"),
        ],
        "query": {},
        "expected_verdict": "healthy",
        "expected_total": 2,
        "expected_internal": 2,
        "expected_live": 2,
        "expected_live_ratio": 1.0,
    },
    {
        "name": "one_dangling",
        "training": [
            _row("a.md", 1, "exists.md", "repo_path", "live"),
            _row("a.md", 2, "missing.md", "repo_path", "dangling_file"),
        ],
        "query": {"receipt": "dangling_file"},
        "expected_verdict": "degraded",
        "expected_dangling": 1,
        "expected_matching_count": 1,
    },
    {
        "name": "external_excluded_from_ratio",
        "training": [
            _row("a.md", 1, "https://example.com", "external", "external"),
            _row("a.md", 2, "ok.md", "repo_path", "live"),
        ],
        "query": {},
        "expected_verdict": "healthy",
        "expected_external": 1,
        "expected_internal": 1,
        "expected_live_ratio": 1.0,
    },
    {
        "name": "empty_dataset",
        "training": [],
        "query": {},
        "expected_verdict": "no_data",
        "expected_total": 0,
    },
]


def _check_probe(probe: dict, fitted: dict, result: dict) -> tuple[bool, dict]:
    checks: dict[str, bool] = {}
    checks["verdict"] = result["verdict"] == probe["expected_verdict"]
    for k in ("total", "internal", "live", "dangling", "external"):
        ek = f"expected_{k}"
        if ek in probe:
            checks[k] = fitted[k] == probe[ek]
    if "expected_live_ratio" in probe:
        checks["live_ratio"] = fitted["live_ratio"] == probe["expected_live_ratio"]
    if "expected_matching_count" in probe:
        checks["matching_count"] = result.get("matching_count") == probe["expected_matching_count"]
    return all(checks.values()), checks


def run_probes() -> list[dict]:
    out: list[dict] = []
    for probe in PROBES:
        fitted = fit(probe["training"])
        result = evaluate(probe["query"], fitted=fitted, training_rows=probe["training"])
        ok, checks = _check_probe(probe, fitted, result)
        out.append({"name": probe["name"], "expected": probe["expected_verdict"],
                    "actual": result["verdict"], "checks": checks, "pass": ok})
    return out
