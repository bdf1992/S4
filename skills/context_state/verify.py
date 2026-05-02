"""verify.py — skill-level self-check for context_state.

Runs the session_turns collector against the live transcript directory and
checks five things:
  1. shape       — every data point validates as Foundation-1 shaped.
  2. liveness    — sampled data points re-verify as 'live' against source.
  3. determinism — collect() produces byte-identical output on re-run.
  4. honesty     — cross-record invariants hold across the full dataset:
                   contiguous turn_index per session starting at 0,
                   monotonic cumulative_bytes_in_session,
                   cumulative tracks the sum of byte_sizes,
                   each session_id resolves to a real transcript file.
  5. completeness — total emitted matches a fresh count from the transcript.

Exits 0 iff every check passes. Prints a one-line summary per check class
plus per-failure detail.

Usage:
  python -m skills.context_state.verify
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from skills.context_state.collectors import session_turns
from skills.context_state.lib import data_point as dp


def main() -> int:
    failures: list[str] = []
    ss = session_turns.compute_source_state()
    dps = session_turns.collect(ss)
    print(f"  collect: source_state={ss} emitted={len(dps)} data points")

    bad_shape = 0
    for d in dps:
        ok, reason = dp.validate(d)
        if not ok:
            bad_shape += 1
            if bad_shape <= 3:
                failures.append(f"shape: {d.get('id', '?')} {reason}")
    print(f"  shape:   {len(dps) - bad_shape}/{len(dps)} valid (Foundation 1)")

    sample = dps[:200] + dps[-200:] if len(dps) > 400 else dps
    bad_live = 0
    for d in sample:
        status, reason = session_turns.verify(d)
        if status != "live":
            bad_live += 1
            if bad_live <= 3:
                failures.append(f"verify: {d['id']} {status}:{reason}")
    print(f"  verify:  {len(sample) - bad_live}/{len(sample)} live "
          f"(sampled head+tail)")

    ss2 = session_turns.compute_source_state()
    determ_ok = ss == ss2
    if determ_ok:
        dps2 = session_turns.collect(ss2)
        canon = lambda xs: [json.dumps({k: v for k, v in d.items()
                                        if k != "provenance"}, sort_keys=True)
                            for d in xs]
        determ_ok = canon(dps) == canon(dps2)
    if not determ_ok:
        failures.append("determinism: source_state or output diverged on re-run")
    print(f"  determ:  {'ok' if determ_ok else 'DIVERGED'}")

    by_session: dict[str, list[dict]] = {}
    for d in dps:
        by_session.setdefault(d["value"]["session_id"], []).append(d["value"])
    bad_honesty = 0
    for sid, vals in by_session.items():
        vals.sort(key=lambda v: v["turn_index"])
        for i, v in enumerate(vals):
            if v["turn_index"] != i:
                bad_honesty += 1
                if bad_honesty <= 3:
                    failures.append(f"honesty: {sid} turn_index_gap "
                                    f"expected {i} got {v['turn_index']}")
                break
        running = 0
        for v in vals:
            running += v["byte_size"]
            if v["cumulative_bytes_in_session"] != running:
                bad_honesty += 1
                if bad_honesty <= 3:
                    failures.append(f"honesty: {sid}#{v['turn_index']} "
                                    f"cum_drift expected {running} "
                                    f"got {v['cumulative_bytes_in_session']}")
                break
        if session_turns._find_session_file(sid) is None:
            bad_honesty += 1
            if bad_honesty <= 3:
                failures.append(f"honesty: {sid} session_file_missing")
    print(f"  honesty: {len(by_session) - bad_honesty}/{len(by_session)} sessions "
          f"pass cross-record invariants")

    fresh_count = 0
    for p in session_turns._files():
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.rstrip()
            if not s:
                continue
            try:
                rec = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                fresh_count += 1
    complete_ok = fresh_count == len(dps)
    if not complete_ok:
        failures.append(f"completeness: emitted {len(dps)} != fresh count {fresh_count}")
    print(f"  complete:{'ok' if complete_ok else 'MISMATCH'}  "
          f"({len(dps)} emitted, {fresh_count} expected)")

    if failures:
        print("\nfailures:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\nverify: all checks passed (exit 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
