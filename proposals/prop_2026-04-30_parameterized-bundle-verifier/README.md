# Parameterized bundle_verifier — design preview

**Status:** design preview, **not** a Foundation-2-verified proposal yet. See "What's missing" below.

## What's here

A draft of what the four hardcoded `verify.py` candidates would collapse into if unified.

```
draft/
├── bundle_verifier.py             # the parameterized library (78 lines)
├── verify_dashboard.py            # shim: 14 lines, manifest only
├── verify_regime_audit_report.py  # shim: 14 lines
├── verify_subprotocol.py          # shim: 19 lines
└── verify_orchestration_audit.py  # shim: 21 lines
```

Each shim declares a manifest (`SKILL_REL`, `PRESENCE`, `PYTHON_AUDIT`) and delegates `collect`/`verify` to the library. In production, the library moves to `skills/bundle_verifier/bundle_verifier.py` and each shim becomes the per-skill `verify.py`.

## Behavioral equivalence to the hardcoded proposals

Run against current source:

| Skill | Hardcoded checks | Parameterized checks | Match |
|---|---|---|---|
| dashboard | 17/17 pass | 17/17 pass | ✅ |
| regime-audit-report | 5/5 pass | 5/5 pass | ✅ |
| subprotocol-for-claude-code | 13/13 pass | 13/13 pass | ✅ |
| orchestration-audit | 11/11 pass | 11/11 pass | ✅ |

All deterministic across two runs.

**One difference from the hardcoded versions:** check_ids change. The library uses a uniform scheme: `<rel-path-with-/-and-.-as-_>_<suffix>`. So `skill_md_present` becomes `skills_dashboard_SKILL_md_present`. Total counts and verdicts are unchanged; only the string identifiers differ. No historical data points exist yet (none of the four hardcoded proposals are promoted), so no migration cost.

## Floor-growth signal

| | Hardcoded | Parameterized |
|---|---|---|
| Lines per new skill | ~78 (full re-implementation) | ~15–20 (manifest only) |
| Total for 4 skills | 4 × ~78 = ~312 | 78 (lib) + 4 × ~17 = ~146 |
| Adding skill #5 | +~78 | +~17 |
| LLM-SDK denylist | duplicated 4× | single source in lib |
| Audit budget per skill | 80 | n/a (lib is 78, shim is trivially auditable) |

This is the SubProtocol "skills floor-growth" pattern: same logic, parameterized, kind-validated. Per-skill emission shrinks from ~78 lines of generative free-write to a ~15-line manifest declaration.

## What's missing to become a Foundation-2 proposal

Per CLAUDE.md, "0.4 is driven by 0.2, not by request." This draft was written because I recommended it and the operator agreed — there is currently **no measured gap** that says "verifiers are unparameterized." That collector does not exist yet.

To upgrade from design preview to proposal:

1. **Build a `verifier_redundancy` gap collector** under `skills/gap_audit/collectors/`. It walks `skills/*/verify.py` (and `proposals/.../candidate/*_verifier.py`), measures structural duplication (shared helpers, identical denylists), and emits a `verifier_redundancy` data point per redundant pattern. That's the 0.2 signal.
2. **Wire this draft as the candidate** that closes the resulting gap data points. Move `bundle_verifier.py` + the 4 shims into the proposal's `candidate/` directory; produce `gap.json`, `pre_verification.json`, `proposal.json`.
3. **Run the existing skill_without_verifier collector** to confirm that promoting this library closes the four `skill_without_verifier:*` gap data points the same way the hardcoded versions do (it does, behaviorally).

Until step 1, this is a 0.0/0.3 design exercise — useful for evaluation, **not yet a 0.4 emission**.

## Two migration paths for the operator

**Path A — sequential (lower risk, slower floor-growth):**
1. Promote one of the four hardcoded proposals now as the 0.4-conformant baseline.
2. Build the `verifier_redundancy` gap collector in a later iteration.
3. Build the parameterized verifier as a measured-gap-driven proposal.
4. Re-promote the four skills onto the parameterized library.

**Path B — replace before any promotion (cleaner end-state, but trades verified work for re-work):**
1. Build the `verifier_redundancy` gap collector now.
2. Replace the four hardcoded proposals with one bundle proposal containing the library + 4 shims.
3. Promote that bundle.

**Path A is the SubProtocol-discipline default** — ship floor first, refine after. Path B is technically cleaner but discards work that's already pre-verified at 80/80, 76/80, 78/80, 74/80.

## Production placement (post-promotion, either path)

```
skills/bundle_verifier/
├── SKILL.md
├── __init__.py
├── bundle_verifier.py        # the library (this draft, parents[2] resolves correctly)
└── verify.py                 # self-check (uses bundle_verifier on itself)
```

Per skill that uses it:

```
skills/<skill>/verify.py     # the manifest shim
```

The `_find_repo_root` helper in the library walks parents looking for `foundations/` + `skills/` siblings, so the same code works in both the draft location (`proposals/.../draft/`) and the production location (`skills/bundle_verifier/`) without path constants needing to change.
