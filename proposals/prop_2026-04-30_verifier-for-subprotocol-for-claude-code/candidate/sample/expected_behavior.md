# Sample — subprotocol_for_claude_code_verifier candidate

The candidate walks the heterogeneous bundle of `skills/subprotocol-for-claude-code/`: SKILL.md, overlay.md, three reference files, two Python scripts. Emits one `bundle_self_check` data point per check.

## Checks (13 total)

7 file-presence checks:
- `SKILL_md_present`, `overlay_md_present`
- `references_domain-configuration-schema_md_present`, `references_domain-configuration_yaml_present`, `references_translation-map_md_present`
- `scripts_setup-interview_py_present`, `scripts_sync_py_present`

6 Python-script audits (3 per script × 2 scripts):
- `{script}_parses`, `{script}_no_llm_sdk`, `{script}_no_nondet` for each of `setup-interview.py` and `sync.py`

## Operational sample

Running against the live skill produces **13/13 pass**.

## Scope boundary (defensible interpretation)

This skill is the prior-art subprotocol that the zero-four-experiment rides under. Its bundle is mostly content (markdown, yaml) with two small utility scripts. The verifier checks structural presence + script cleanliness — it does NOT validate the markdown or yaml contents (that would require a markdown/yaml schema, outside the scope of a per-skill verify.py at this stage).

Reports under `reports/` are NOT checked for presence; they're dated artifacts (e.g. `sync-2026-04-29.md`) that come and go. Adding them to `INPUTS` would make the source_state churn on every sync. If the operator wants reports validated, that's an explicit promotion-time decision and would extend this candidate before promotion.
