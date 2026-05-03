"""Hand-play 003: scrum + fan_out cook over scrum.next_targets[0].skills.

Walks the runner's tick loop manually, capturing each decision. Real source
calls throughout (no mocks of the rituals). Persists trace 003 to
runner_trace.jsonl on completion."""
import datetime
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.cook_session import (
    cook_gate,
    cook_idempotency_key,
    write_session,
)
from tools.heartbeat_template import render
from tools.standup import (
    _last_receipt,
    heartbeat_gate as scrum_gate,
)

trace_decisions = []


def log(step, action, **kw):
    rec = {"step": step, "action": action, **kw}
    trace_decisions.append(rec)
    flat = " ".join(f"{k}={v!r}" for k, v in kw.items() if k != "deterministic")
    print(f"  step {step:>2}: {action}  {flat}")


print("=== Hand-play 003: scrum + fan_out cook ===\n")

# Step 1
log(1, "discover_config", input_="heartbeats/scrum_fanout_cook.toml", deterministic=True)
# Step 2
log(2, "schedule_check", output="fire (operator-triggered)", deterministic=True)

# === step scrum ===
# Step 3
log(3, "load_step", input_="step.id=scrum, skill=scrum", deterministic=True)
# Step 4
contract_scrum = json.loads(
    (REPO / ".claude/skills/scrum/heartbeat.json").read_text(encoding="utf-8")
)
log(4, "discover_ritual_contract",
    output=".claude/skills/scrum/heartbeat.json", deterministic=True)
# Step 5
log(5, "resolve_gate_pointer",
    output="tools.standup.heartbeat_gate", deterministic=True)
# Step 6
scrum_receipt_dir = contract_scrum["receipt_dir"]
gate_result = scrum_gate(scrum_receipt_dir)
log(6, "evaluate_gate", input_=scrum_receipt_dir,
    output=gate_result, deterministic=True)

step_outputs = {}
if gate_result:
    log(7, "dispatch", output="not exercised in 003", deterministic=True)
else:
    last = _last_receipt(REPO / scrum_receipt_dir)
    sidecar_path = REPO / last["sidecar_path"]
    cached = json.loads(sidecar_path.read_text(encoding="utf-8"))
    step_outputs["scrum"] = cached
    log(7, "load_cached_output_from_receipt",
        input_=str(sidecar_path.relative_to(REPO)),
        output=f"loaded scrum sidecar with {len(cached.get('next_targets', []))} buckets",
        deterministic=True,
        _GAP_REF="GAP-20")

# === step cook_targets ===
# Step 8
log(8, "load_step", input_="step.id=cook_targets, skill=cook", deterministic=True)
# Step 9
contract_cook = json.loads(
    (REPO / ".claude/skills/cook/heartbeat.json").read_text(encoding="utf-8")
)
log(9, "discover_ritual_contract",
    output=".claude/skills/cook/heartbeat.json", deterministic=True)
# Step 10
log(10, "resolve_dependencies", input_="depends=[scrum]",
    output="scrum present in step_outputs", deterministic=True)
# Step 11
fan_out_template = "{{ steps.scrum.next_targets[0].skills }}"
items = render(fan_out_template, {"steps": step_outputs})
log(11, "render_fan_out", input_=fan_out_template,
    output=f"items={items}", deterministic=True)

# Per-item dispatch loop
fan_out_results = []
sub_step = 12
for i, item in enumerate(items):
    print(f"\n  --- fan_out item {i}: {item!r} ---")
    bindings = {"steps": step_outputs, "item": item}
    args_template = {"target": "{{ item }}", "mode": "solve"}
    args = render(args_template, bindings)
    log(sub_step, f"render_args[item={i}]", output=args, deterministic=True)
    sub_step += 1

    required = contract_cook.get("required_args", [])
    missing = [k for k in required if k not in args]
    log(sub_step, f"validate_required_args[item={i}]",
        output=f"required={required}, missing={missing}", deterministic=True)
    sub_step += 1
    if missing:
        log(sub_step, f"abort_item[item={i}]",
            output=f"missing: {missing}", deterministic=True)
        sub_step += 1
        continue

    cook_state = {"target": args["target"], "mode": args["mode"]}
    g = cook_gate(contract_cook["receipt_dir"], cook_state)
    log(sub_step, f"cook_gate[item={i}]", input_=cook_state,
        output=g, deterministic=True)
    sub_step += 1
    if not g:
        log(sub_step, f"skip_item[item={i}]",
            output="cached", deterministic=True)
        sub_step += 1
        continue

    k = cook_idempotency_key(contract_cook["receipt_dir"], cook_state)
    log(sub_step, f"cook_key[item={i}]", output=k, deterministic=True)
    sub_step += 1

    sidecar_path = write_session(
        target=args["target"],
        output_dir=contract_cook["output_dir"],
        mode=args["mode"],
        showcase=(
            "[hand-play 003 simulation] cook would have worked on "
            + args["target"]
            + " as a peer-flat isolated_with_signals candidate. "
            + "Real subagent dispatch is GAP-18."
        ),
        commits_landed=[],
        net_loc=0,
        files_touched=0,
        exit_code=0,
        surface="agent-subagent",
    )
    log(sub_step, f"dispatch_cook[item={i}]",
        input_={"surface": "agent-subagent (simulated)", "args": args},
        output={"sidecar": str(sidecar_path.relative_to(REPO))},
        deterministic=False,
        _GAP_REF="GAP-18")
    sub_step += 1

    sidecar_dict = json.loads(sidecar_path.read_text(encoding="utf-8"))
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    fired_at = datetime.datetime.now(
        datetime.timezone.utc
    ).replace(microsecond=0).isoformat()
    receipt = {
        "ritual_id": "ritual:cook",
        "fired_at": fired_at,
        "git_head_at_fire": head,
        "idempotency_key": k,
        "output_path": str(sidecar_path.relative_to(REPO)),
        "sidecar_path": str(sidecar_path.relative_to(REPO)),
        "dispatch_surface": "agent-subagent (simulated)",
        "exit_code": 0,
        "trace_id": "trace:003",
        "parent_step": "cook_targets",
        "fan_out_index": i,
        "args_after_substitution": args,
    }
    rec_dir = REPO / contract_cook["receipt_dir"]
    rec_dir.mkdir(parents=True, exist_ok=True)
    rec_path = rec_dir / f"{sidecar_dict['session_id']}.receipt.json"
    rec_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    log(sub_step, f"write_receipt[item={i}]",
        output=str(rec_path.relative_to(REPO)), deterministic=True)
    sub_step += 1
    fan_out_results.append(sidecar_dict)

log(sub_step, "aggregate_fan_out",
    output=f"{len(fan_out_results)} sub-results aggregated",
    deterministic=True,
    _GAP_REF="GAP-21")
step_outputs["cook_targets"] = fan_out_results

print(f"\n=== Tick complete: {len(trace_decisions)} steps, {len(fan_out_results)} cooks dispatched ===")

trace_record = {
    "trace_id": "trace:003",
    "config_path": "heartbeats/scrum_fanout_cook.toml",
    "config_hash": None,
    "fired_at": datetime.datetime.now(
        datetime.timezone.utc
    ).replace(microsecond=0).isoformat(),
    "wall_clock_source": "operator-triggered (hand-play 003)",
    "preconditions_closed_since_002": [
        "GAP-14 closed: heartbeat_gate/idempotency_key now take receipt_dir",
        "GAP-15 closed: tools/heartbeat_template.py supports dotted, [N], [:N], item binding",
    ],
    "decision_sequence": trace_decisions,
    "fan_out_count": len(fan_out_results),
    "fan_out_items": items,
    "step_outputs_keys": list(step_outputs.keys()),
    "exit_code": 0,
    "gaps_surfaced": ["GAP-20", "GAP-21", "GAP-22"],
    "gaps_closed_since_002": ["GAP-14", "GAP-15"],
    "stable_steps": [s["step"] for s in trace_decisions if s.get("deterministic")],
    "judgment_call_steps": [
        s["step"] for s in trace_decisions if not s.get("deterministic")
    ],
    "ratio_deterministic": (
        f"{sum(1 for s in trace_decisions if s.get('deterministic'))}/"
        f"{len(trace_decisions)}"
    ),
}
with (REPO / "traces/runner_trace.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(trace_record) + "\n")
print(f"\nappended trace:003 ({trace_record['ratio_deterministic']} deterministic) to runner_trace.jsonl")
