# Sample — dashboard_verifier candidate

The candidate reads live source under `skills/dashboard/` (declared in `INPUTS`) and emits one `bundle_self_check` data point per file-level structural check. Checks are batched programmatically: 1 for `SKILL.md` + 4 per Python entry point × 4 entry points = **17 total**.

| File | Checks |
| --- | --- |
| `SKILL.md` | `skill_md_present` |
| `render.py`, `snapshot.py`, `narrate.py`, `html.py` | `{file}_present`, `{file}_parses`, `{file}_no_llm_sdk`, `{file}_no_nondet` |

## Operational sample

Running against the live `skills/dashboard/` at proposal-time produces **17/17 pass**:

```
  skill_md_present: pass (exists)
  render.py_present: pass (exists)
  render.py_parses: pass (parses)
  render.py_no_llm_sdk: pass (clean)
  render.py_no_nondet: pass (clean)
  snapshot.py_present / parses / no_llm_sdk / no_nondet: pass
  narrate.py_present / parses / no_llm_sdk / no_nondet: pass
  html.py_present / parses / no_llm_sdk / no_nondet: pass
```

Re-running produces byte-identical witnesses (provenance.collected_at differs but is advisory).

## Scope boundary

dashboard is a multi-entry-point render skill with no collectors or signals. The verifier checks file-level structural and import-cleanliness predicates over the four Python entry points. It does NOT exercise the entry points end-to-end (would require fixture inputs and a 4.0 bundle harness, both outside the scope of a per-skill verify.py at this stage).

If the operator wants richer verification (fixture-based render output diff, snapshot reproducibility check), that is an explicit promotion-time decision and would extend this candidate before promotion.
