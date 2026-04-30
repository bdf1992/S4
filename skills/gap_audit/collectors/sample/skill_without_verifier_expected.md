# Sample — skill_without_verifier collector

This collector reads live source (`skills/*/SKILL.md` and `skills/*/verify.py`) at the current source_state. There is no synthetic-input file because the source-walk is over the actual skills directory; the collector is deterministic against repo state, and a snapshot of that state at a given commit is a sufficient sample.

## Expected behavior

For each subdirectory `skills/{name}/` that contains `SKILL.md`:

| Condition | `collect()` emits |
| --- | --- |
| `verify.py` is present | nothing (this skill is not a gap) |
| `verify.py` is absent | one `skill_without_verifier` data point |

Each emitted data point has:

- `kind == "skill_without_verifier"`
- `value.skill_pointer.kind == "file_path"`
- `value.skill_pointer.target.path == "skills/{name}"`
- `value.looked_for == ["skills/{name}/verify.py"]`
- `provenance.collector.target.collector_id == "skill_without_verifier"`

## Live-source assertion (the operational sample)

At commit `1421c0e` (after the proposal-contract amendment), the live source contains:

- `claim_audit/`, `leash_for_hooks/`, `leash_for_slash_commands/`, `regime_audit/` — each has both `SKILL.md` and `verify.py` (no gap)
- `dashboard/`, `regime_audit_report/`, `subprotocol-for-claude-code/` — each has `SKILL.md` but no `verify.py` (gap)
- `gap_audit/` — does not yet have `SKILL.md`; not evaluated by this collector

Therefore `collect()` against the current state should emit exactly **3** data points.
