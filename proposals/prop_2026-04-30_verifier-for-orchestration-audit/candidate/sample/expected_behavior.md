# Sample — orchestration_audit_verifier candidate

The candidate reads live source under `skills/orchestration_audit/` (declared in `INPUTS`) and emits one `bundle_self_check` data point per file-level structural check. Checks are batched programmatically: 1 for `SKILL.md` + 4 per Python entry point × 2 entry points + 2 dataset-presence checks = **11 total**.

| File | Checks |
| --- | --- |
| `SKILL.md` | `skill_md_present` |
| `collectors/orchestration_activations.py`, `lib/data_point.py` | `{name}_present`, `{name}_parses`, `{name}_no_llm_sdk`, `{name}_no_nondet` |
| `datasets/orchestration_activations.jsonl`, `datasets/orchestration_activations.source_state` | `{name}_present` |

## Operational sample

Running against the live `skills/orchestration_audit/` at proposal-time produces **11/11 pass**:

```
  skill_md_present: pass (exists)
  orchestration_activations.py_present: pass (exists)
  orchestration_activations.py_parses: pass (parses)
  orchestration_activations.py_no_llm_sdk: pass (clean)
  orchestration_activations.py_no_nondet: pass (clean)
  data_point.py_present: pass (exists)
  data_point.py_parses: pass (parses)
  data_point.py_no_llm_sdk: pass (clean)
  data_point.py_no_nondet: pass (clean)
  orchestration_activations_jsonl_present: pass (exists)
  orchestration_activations_source_state_present: pass (exists)
```

Re-running produces byte-identical witnesses (provenance.collected_at differs but is advisory).

## Scope boundary

orchestration_audit is a Foundation-2 collector skill — one collector module + one local lib + one dataset, no orchestrate.py, no signals/ yet. The verifier checks file-level structural and import-cleanliness predicates over the two Python files plus presence of the collector-produced dataset. It does NOT exercise the collector against fresh source (would require a full orchestration corpus to walk, and a 0.4 bundle harness, both outside the scope of a per-skill verify.py at this stage).

The dataset-presence checks are load-bearing for this skill: orchestration_audit's claim is "0.3 self-report → 0.1 measurement," and the measurement only exists if the collector has been run and the dataset persisted. A missing dataset is a real failure, not a stylistic miss.

If the operator wants richer verification (collector re-run determinism check, dataset row schema validation, signal/orchestration audits if those are added later), that is an explicit promotion-time decision and would extend this candidate before promotion.
