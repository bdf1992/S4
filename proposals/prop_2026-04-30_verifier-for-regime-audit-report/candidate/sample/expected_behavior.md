# Sample — regime_audit_report_verifier candidate

The candidate reads live source under `skills/regime_audit_report/` (declared in `INPUTS`) and emits one `bundle_self_check` data point per structural check it performs. Five checks are declared in `collect()`:

| `check_id` | What it verifies |
| --- | --- |
| `skill_md_present` | `skills/regime_audit_report/SKILL.md` is a regular file |
| `render_py_present` | `skills/regime_audit_report/render.py` is a regular file |
| `render_py_parses` | `render.py` is syntactically valid Python (AST parse succeeds) |
| `render_py_no_llm_sdk` | `render.py` imports nothing from the LLM-SDK denylist |
| `render_py_no_nondet` | `render.py` imports nothing from the nondeterminism denylist |

## Operational sample

Running the candidate against the live source at proposal-time produces:

```
  skill_md_present: pass (exists)
  render_py_present: pass (exists)
  render_py_parses: pass (parses)
  render_py_no_llm_sdk: pass (clean)
  render_py_no_nondet: pass (clean)

5/5 checks passed
```

All 5 emitted records validate against `value_schema.json`. Re-running produces byte-identical witnesses (modulo `provenance.collected_at`, which is advisory per [foundations/data-point.md](../../../foundations/data-point.md)).

## Scope boundary (defensible interpretation)

regime_audit_report is a *render* skill — it is a pure 1.0 deterministic transform from `stats.json` to `report.md`, with no collectors, signals, or orchestration. The verifier therefore checks structural and import-cleanliness predicates rather than walking a 4.0-bundle `manifest.json` (there is none). This is a smaller verifier than the one shipped with `regime_audit` (188 lines vs. 134 here), proportional to the smaller bundle surface. If the operator wants render skills to be held to a richer standard (e.g., re-run determinism on a fixture), that's an explicit promotion-time decision and would extend this candidate before promotion.
