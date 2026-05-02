# Mutation operator catalog — design preview

**Status:** design preview, **not** a Foundation-2-verified proposal yet. See "What's missing" below. This document is a 0.1 spec draft for the schema a mutation-testing pipeline would consume; it does not ship code, a runner, or a gap collector. Authored by a 3.0 routine in response to an operator framing turn (see [transcript pointer at end]) — not yet anchored to a measured gap.

This file uses the two-axis programs-vs-protocols framing from [CLAUDE.md](../../CLAUDE.md): X.0 names program kinds (1.0 handwritten, 2.0 learned, 3.0 prompted, 4.0 coupled); 0.X names the protocols that produce them; 0.0 is the candidate state.

---

## What this catalog is

A **mutation operator catalog** is a 0.1 schema declaring the set of structural perturbations a mutation-runner is allowed to apply to a target program or bundle. It is the floor that the eventual mutation-runner (a 1.0 program), the runner's honesty auditor (a 1.0 program), and the resulting kill-rate dataset (which a 2.0 model could later be trained on) all attach to.

The catalog is **authored, not generated.** A mutation operator that an LLM emits per-run is not a 0.1 entity; it is a 3.0 free-write claiming to be a primitive. For the dataset of `(operator, site, mutant_hash, test_outcome)` records to ground anything, the operator names and shapes must be a fixed, kind-validated, versioned set. The runner picks operators *from* the catalog; it does not *invent* them.

The catalog is **structural, not stochastic.** A catalog entry declares a deterministic site-enumeration function and a deterministic mutation function, both keyed by `(target, seed)`. There are no probability distributions in the catalog — distributions belong to a 2.0 layer that may later learn which operators are worth applying more often. The 0.1 floor is "what mutations exist and how to apply them deterministically," nothing more.

## Catalog entry shape

A catalog entry is a record with exactly these fields. A record missing any field, or carrying additional fields, is not a valid catalog entry.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `operator_id` | string | yes | Stable handle. Format: `mut:{family}:{slug}`. Slug is `[a-z0-9_]+`. Examples: `mut:source:boolean_flip`, `mut:semantic:pointer_target_swap`. |
| `family` | enum | yes | One of `source_mutation` \| `semantic_mutation`. Source-family mutates a 1.0 program's source code; semantic-family mutates a bundle artifact (data point, pointer, receipt, manifest). |
| `applies_to` | typed-by-family | yes | Source-family: list of Python AST node types this operator targets (e.g. `["BoolOp", "Compare"]`). Semantic-family: list of artifact kinds (e.g. `["data_point:line_count", "pointer:file_line"]`). |
| `enumerate_sites_pointer` | pointer ([Foundation 3](../../foundations/pointer.md)) | yes | `kind=symbol`. Resolves to a deterministic function `enumerate_sites(target_state) → list[site_id]`. Same target_state, same site list, every time. |
| `apply_mutation_pointer` | pointer | yes | `kind=symbol`. Resolves to a deterministic function `apply_mutation(target_state, site_id, seed) → mutated_target_state`. Pure: no I/O outside the target, no clock, no LLM. |
| `expected_to_be_caught_by` | enum | yes | One of `target_test_suite` \| `bundle_verify` \| `bundle_validate`. Declares which discipline this operator's survival measures. A `source_mutation` operator typically declares `target_test_suite`; a `semantic_mutation` operator typically declares `bundle_verify`. |
| `catalog_version` | string | yes | Semver of the catalog this entry belongs to. Stamped into every dataset record so corpus rows stay interpretable across catalog edits. |
| `audit_budget_lines` | integer | yes | Maximum substantive line count the `apply_mutation` function may have. Mutation functions are subject to the same audit-budget discipline as collectors ([Foundation 2](../../foundations/collection-program.md)) — a complex mutation function can quietly mutate the wrong thing. |

There is no free-text `description`, `intent`, or `notes` field. If a 3.0 process wants to record motivation for an operator's existence, it does so in its own log; the catalog entry stays structural.

## Catalog file shape

A catalog is a directory `mutation_catalog/` containing exactly:

| Item | Meaning |
| --- | --- |
| `catalog.json` | List of catalog entries (records as above). Schema-validated on load. |
| `operators/{operator_id}.py` | One source file per entry, exporting `enumerate_sites` and `apply_mutation`. Each file passes [collection-program.md](../../foundations/collection-program.md)'s structural validators (audit budget, no LLM imports, no nondeterminism). |
| `version.txt` | The catalog's semver, matching every entry's `catalog_version`. Bump on any operator add/remove/change. |

The catalog is itself a 1.0-shaped artifact: deterministic, auditable, no LLM. Entries are added by hand or by a promoted proposal (just like collectors); they are never added by a runtime LLM call.

## How the catalog plugs into the runner (sketch)

This section sketches the consumer interface so the catalog's shape can be evaluated against its eventual use. **The runner itself is not specified here** — it is a separate 0.1 spec, deferred to its own document once the catalog stabilizes.

```
runner.run(target, catalog, seed) -> list[mutation_record]

  for operator in catalog.entries:
      sites = operator.enumerate_sites(target)
      for site_id in sites:
          mutant = operator.apply_mutation(target, site_id, seed)
          outcome = run_expected_discipline(mutant, operator.expected_to_be_caught_by)
          emit mutation_record(
              operator_id   = operator.operator_id,
              site_id       = site_id,
              mutant_hash   = hash(mutant),
              outcome       = outcome,        # killed | survived | error
              catalog_version = operator.catalog_version,
              target_hash   = hash(target),
              seed          = seed,
          )
```

Each `mutation_record` is shaped as a [Foundation-1 data point](../../foundations/data-point.md) with `kind = mutation_outcome` and a `value_schema` covering the fields above. The runner is a [Foundation-2 collector](../../foundations/collection-program.md): single-kind output, deterministic, no LLM. The `mutation_outcome` records accumulate into a corpus that is computed-not-authored by construction.

## Detectable violations

Each violation MUST be detectable by a 0.1 program. A violation requiring human or model judgement indicates a hole in this catalog spec.

| Violation | How it is detected |
| --- | --- |
| Required field missing or extra field present in a catalog entry | Schema validator on `catalog.json`. |
| `operator_id` does not match `mut:{family}:{slug}` format | Format validator. |
| `family` value is not in the allowed enum | Schema validator. |
| `applies_to` contains AST node types or artifact kinds the runner does not recognize | Cross-check against the runner's registry of known target shapes. |
| `enumerate_sites_pointer` or `apply_mutation_pointer` dangles | Pointer re-resolution at run-time ([Foundation 3](../../foundations/pointer.md)). |
| The function under `apply_mutation_pointer` imports an LLM SDK or uses a banned source of nondeterminism | Foundation-2 static check on the operator's source file. |
| Two runs of `enumerate_sites(target_state)` produce different site lists | Determinism check; reject the entry. |
| Two runs of `apply_mutation(target, site_id, seed)` produce different mutated targets | Determinism check; reject the entry. |
| `apply_mutation` writes outside the mutated target (e.g., to disk, to network, to source) | Sandboxed execution: any write outside the in-memory target buffer fails the entry. |
| `audit_budget_lines` exceeded by the operator's source file | Static line count; reject the entry. |
| `catalog_version` in an entry disagrees with `version.txt` | Cross-file consistency check on load. |
| `expected_to_be_caught_by` names a discipline that does not exist for the target's bundle kind | Cross-check against the bundle's declared verifies/validates. |
| Entry added without a corresponding promoted proposal trace | Catalog audit: every entry either pre-dates this contract or has a trace back to a `promoted` mutation-operator proposal. |

A catalog entry failing any check is removed from the active catalog. Mutation records produced under an invalidated entry are quarantined (their `catalog_version` makes them identifiable in the corpus).

## What this catalog is not

- **Not a 1.0 program.** The catalog is a schema and a directory of operator source files. The mutation-runner that consumes the catalog is the 1.0 program; this is the floor under it.
- **Not a generator.** The catalog does not produce mutants on demand based on natural-language description. Each entry is a hand-authored deterministic function with declared site enumeration. An operator that "intelligently figures out where to mutate" is a 3.0 free-write, not a catalog entry.
- **Not a 2.0 signal.** Kill rates, survivor patterns, and operator-importance weights are 2.0 concerns. The catalog declares only what mutations exist and how to apply them; it does not say which mutations matter more.
- **Not a quality gate.** A run of the catalog against a target produces a dataset; the dataset is the substrate that makes a 2.0 signal possible (and eventually a 0.3-fenced `validate` discipline). The catalog itself does not gate anything.
- **Not bedrock.** This contract is derived. It can be revised when experience shows it should be — every revision bumps `version.txt` and stamps every subsequent record. The four foundations remain the immovable layer; this file is wiring under them.

## Why this shape

Each constraint exists to close a specific failure mode at the catalog level (the foundations close failure modes at the primitive level):

- **Authored, not generated, operators** close *LLM-graded LLM-mutants*. If both sides of the test (mutant generation and verify-walking) drift together, kill-rate means nothing. Hand-authored operators are independent of the LLM that writes verify.py.
- **Deterministic site enumeration** closes *seed leakage*. A nondeterministic site list means two runs with the same seed disagree; the corpus stops being reproducible; the dataset stops being a measurement.
- **Audit budget on `apply_mutation`** closes *quiet semantic drift*. A long mutation function can silently mutate the wrong thing (e.g., flip a flag *and* delete a log line); a small one cannot hide that.
- **`catalog_version` stamped per record** closes *corpus drift across catalog edits*. Without it, adding an operator silently invalidates every prior survivor count for that target. With it, every edit is visible in the dataset's distribution.
- **`expected_to_be_caught_by` enum** closes *grading-discipline ambiguity*. A surviving mutant is only meaningful if the discipline expected to catch it is named — otherwise "survived" could mean "verify didn't cover it" or "verify ran but didn't assert on it" or "no test exists at all."
- **Family split (`source_mutation` vs `semantic_mutation`)** closes *operator-confusion across rungs*. A boolean-flip on Python source is a different shape from a pointer-target-swap on a bundle artifact; collapsing them would force the catalog into a lowest-common-denominator schema that captures neither well.

Holding all of these at once is what lets the mutation-testing pipeline grow under discipline. Operators are added one at a time, each one a small auditable file; the corpus accumulates per-operator survival data; eventually a 2.0 signal trains over the corpus and tells a 0.3 layer where the test/verify holes are.

## What's missing to become a Foundation-2-verified proposal

Per [CLAUDE.md](../../CLAUDE.md), "0.4 emits 4.0 only when 2.0 signals fire." This draft was written because the operator framed mutation testing as a signal-collection pattern and asked for the catalog spec — there is currently **no measured gap** that says "mutation testing is absent." That collector does not exist yet.

To upgrade from design preview to proposal:

1. **Build a `mutation_coverage` gap collector** under [skills/gap_audit/collectors/](../../skills/gap_audit/collectors/). It walks every 1.0 collector under `skills/*/collectors/` (and every `verify.py` under `skills/*/`) and emits a `mutation_coverage` data point per target with no associated mutation-test record at the current source state. Today, every collector and every verify.py would emit a gap data point — the gap is real and dense.

2. **Wire this catalog draft as the candidate** that the proposal would draft *next*. The first catalog entry would be a single source-mutation operator (e.g., `mut:source:boolean_flip` borrowing mutmut's shape) — small enough to author and exercise end-to-end against one collector before any breadth.

3. **Build the mutation-runner spec** in its own design-preview doc (`prop_2026-05-XX_mutation-runner/`), referencing this catalog as its 0.1 floor. The runner spec is deferred until the catalog shape is reviewed.

4. **Build the runner's honesty auditor** (a sibling 1.0 collector) that verifies, for each `mutation_outcome` record, that the outcome reproduces from `(target_hash, operator_id, site_id, seed, catalog_version)`. Without this, "5% survivor rate" is unverifiable and the corpus cannot ground a 2.0.

Until step 1, this is a 0.0-stage design exercise authored by a 3.0 — useful for evaluation, **not yet a 4.0 emission**.

## Operator transcript pointer

Operator framing turns that authorize this draft, in chronological order:

- "mutation can also be a test on one point O program ... it is a test pattern for 1.0 as well" — established that the catalog must span both source-family (1.0 source mutation) and semantic-family (bundle artifact mutation).
- "if we install [logging] programs then we do mutation testing we can begin to understand our survivor what can then be modeled as a data set" — established the chain target: catalog → runner → corpus → 2.0 model. Reframed mutation testing as signal-collection, not quality gate. This reordered the priority and is the load-bearing framing this spec is shaped against.
- "yes" to "Do you want me to draft the operator catalog (0.1 spec) first? It's the floor the runner and auditor both attach to, and it's pure spec work — no code or tooling commitments yet."

Per the operator-intent-via-transcript-pointer discipline, the verbal directive in the session transcript is the authorization for this draft. The transcript file lives at `~/.claude/projects/{project_path}/{session}.jsonl`; the three turns above appear in sequence on 2026-05-01.
