"""0.2 signal — symphony_permission_posture.

Question answered: does a candidate WORKFLOW.md flip the operator's
established permission posture (the values for claude.skip_permissions,
claude.permission_mode, codex.approval_policy, codex.thread_sandbox) vs.
the corpus mode? Also: does the candidate satisfy the cross-field
unattended-operation rule?

Fitting: walks the symphony_workflow dataset; the fitted parameter is
the per-key mode value (most-common observed) over the training rows,
plus the training row count. Re-fitting is deterministic and itself a
0.1 program.

Verdict semantics for evaluate():
  posture_consistent — every posture key in the candidate matches the
    corpus mode (or the corpus is empty / the key is absent in both).
  posture_drift — at least one posture key in the candidate disagrees
    with a non-empty corpus mode, e.g. corpus mode says
    skip_permissions=False but candidate sets skip_permissions=True.

Verdict semantics for check_permission_config():
  permission_config_ok — claude.skip_permissions=true OR
    claude.allowed_tools is a non-empty list; unattended operation is
    safe.
  permission_config_error — neither condition holds; unattended
    operation would proceed without any permission fence, matching the
    cc-symphony upstream validation error of the same name.

On an empty corpus the verdict is posture_consistent with confidence 0
— the same shape slash_command_collision uses for empty training.

Probe set: four synthetic inputs whose expected verdicts are recorded as
literals; verify.py runs the probes against the signal to confirm
fit-time behavior holds at verification time."""
from __future__ import annotations

from collections import Counter

SIGNAL_ID = "symphony_permission_posture"
TRAINING_DATASET_KIND = "symphony_workflow"
VERDICT_ENUM = ("posture_consistent", "posture_drift")
PERMISSION_CONFIG_VERDICT_ENUM = ("permission_config_ok", "permission_config_error")

POSTURE_KEYS = (
    "claude_skip_permissions",
    "claude_permission_mode",
    "codex_approval_policy",
    "codex_thread_sandbox",
)


def fit(training_rows: list[dict]) -> dict:
    """Returns {key: mode_value} for each posture key with a non-None
    majority value across the training rows. Keys with no observed
    non-None value are omitted from the fitted dict."""
    counters: dict[str, Counter] = {k: Counter() for k in POSTURE_KEYS}
    for r in training_rows:
        posture = (r.get("value") or {}).get("permission_posture") or {}
        for k in POSTURE_KEYS:
            val = posture.get(k)
            if val is not None:
                counters[k][_freezable(val)] += 1
    fitted: dict[str, object] = {}
    for k, c in counters.items():
        if c:
            fitted[k] = _unfreeze(c.most_common(1)[0][0])
    return fitted


def _freezable(v):
    if isinstance(v, list):
        return ("__list__", tuple(v))
    return v


def _unfreeze(v):
    if isinstance(v, tuple) and len(v) == 2 and v[0] == "__list__":
        return list(v[1])
    return v


def _candidate_posture(candidate: dict) -> dict:
    return {
        "claude_skip_permissions": (candidate.get("claude") or {}).get("skip_permissions"),
        "claude_permission_mode":  (candidate.get("claude") or {}).get("permission_mode"),
        "codex_approval_policy":   (candidate.get("codex")  or {}).get("approval_policy"),
        "codex_thread_sandbox":    (candidate.get("codex")  or {}).get("thread_sandbox"),
    }


def evaluate(candidate: dict, *, fitted_modes: dict,
             training_rows: list[dict]) -> dict:
    """Returns {verdict, confidence, evidence_pointers, drifted_keys}."""
    cand_posture = _candidate_posture(candidate)
    drifted = []
    for k, mode_val in fitted_modes.items():
        cand_val = cand_posture.get(k)
        if cand_val is not None and cand_val != mode_val:
            drifted.append({"key": k, "candidate": cand_val, "corpus_mode": mode_val})
    if not training_rows:
        return {"verdict": "posture_consistent", "confidence": 0.0,
                "evidence_pointers": [], "drifted_keys": []}
    if drifted:
        evidence = [
            {"kind": "data_point", "target": {"dp_id": r["id"]},
             "resolver": "data_point_resolver"}
            for r in training_rows
        ]
        return {"verdict": "posture_drift",
                "confidence": min(1.0, len(training_rows) / 5.0),
                "evidence_pointers": evidence,
                "drifted_keys": drifted}
    return {"verdict": "posture_consistent",
            "confidence": min(1.0, len(training_rows) / 5.0),
            "evidence_pointers": [], "drifted_keys": []}


def check_permission_config(candidate: dict) -> dict:
    """Cross-field rule: unattended operation requires either
    claude.skip_permissions=true OR a non-empty claude.allowed_tools list.
    Returns {verdict, reason} where verdict is one of
    PERMISSION_CONFIG_VERDICT_ENUM."""
    claude = candidate.get("claude") or {}
    skip = claude.get("skip_permissions")
    tools = claude.get("allowed_tools")
    if skip is True:
        return {"verdict": "permission_config_ok", "reason": "skip_permissions_true"}
    if isinstance(tools, list) and tools:
        return {"verdict": "permission_config_ok", "reason": "allowed_tools_non_empty"}
    return {"verdict": "permission_config_error",
            "reason": "neither skip_permissions=true nor non-empty allowed_tools"}


PROBES: list[dict] = [
    {
        "name": "drift_detected",
        "kind": "posture",
        "training": [{"id": "symphony_workflow:probe1", "value": {
            "permission_posture": {
                "claude_skip_permissions": False,
                "claude_permission_mode": "default",
                "codex_approval_policy": None,
                "codex_thread_sandbox": None,
            },
        }}],
        "candidate": {"claude": {"skip_permissions": True}},
        "expected_verdict": "posture_drift",
    },
    {
        "name": "consistent_with_corpus",
        "kind": "posture",
        "training": [{"id": "symphony_workflow:probe1", "value": {
            "permission_posture": {
                "claude_skip_permissions": False,
                "claude_permission_mode": "default",
                "codex_approval_policy": None,
                "codex_thread_sandbox": None,
            },
        }}],
        "candidate": {"claude": {"skip_permissions": False, "permission_mode": "default"}},
        "expected_verdict": "posture_consistent",
    },
    {
        "name": "permission_config_ok_via_allowed_tools",
        "kind": "permission_config",
        "candidate": {"claude": {"skip_permissions": False,
                                 "allowed_tools": ["Bash", "Read"]}},
        "expected_verdict": "permission_config_ok",
    },
    {
        "name": "permission_config_error_no_fence",
        "kind": "permission_config",
        "candidate": {"claude": {"skip_permissions": False, "allowed_tools": []}},
        "expected_verdict": "permission_config_error",
    },
]


def run_probes() -> list[dict]:
    out = []
    for probe in PROBES:
        kind = probe.get("kind", "posture")
        if kind == "permission_config":
            result = check_permission_config(probe["candidate"])
            out.append({"name": probe["name"], "expected": probe["expected_verdict"],
                        "actual": result["verdict"],
                        "pass": result["verdict"] == probe["expected_verdict"]})
        else:
            fitted = fit(probe["training"])
            result = evaluate(probe["candidate"], fitted_modes=fitted,
                              training_rows=probe["training"])
            out.append({"name": probe["name"], "expected": probe["expected_verdict"],
                        "actual": result["verdict"],
                        "pass": result["verdict"] == probe["expected_verdict"]})
    return out
