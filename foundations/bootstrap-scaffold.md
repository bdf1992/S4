# Bootstrap-scaffold contract — derived

**Status:** DERIVED. This contract sits on top of the four bedrock foundations ([data-point.md](data-point.md), [collection-program.md](collection-program.md), [pointer.md](pointer.md), [zero-four.md](zero-four.md)) and is revisable without a 4.0 grading event. It is NOT bedrock. The four foundations remain immutable; this file is the wiring under them for one specific situation — adopting an external tool as a *temporary spec/proposal-authoring scaffold* during the chain's bootstrap, and the conditions under which the chain absorbs it and the scaffold retires.

Vocabulary is from [CLAUDE.md](../CLAUDE.md): X.0 = program kind (1.0 handwritten, 2.0 learned, 3.0 prompted, 4.0 coupled); 0.X = the protocol that produces it; 0.0 = candidate state.

---

## What a bootstrap scaffold is

A **bootstrap scaffold** is an external program — not authored under the chain's discipline, not a 1.0/2.0/3.0 in our register — that the operator adopts to fill a slot the chain cannot yet fill itself. It rides during the chain's bootstrap, produces artifacts the chain consumes, and is retired into the chain when the chain demonstrates **feature parity** (the central predicate of this contract) for that slot.

A scaffold is **not** bedrock and **not** a graduated component. It is a tolerated tenant. Adoption is explicit; retirement is signal-gated; and the period of tenancy is bounded by a written parity surface that cannot quietly grow.

The first scaffold this contract governs is **OpenSpec** ([github.com/Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec)). Future scaffolds, if any, are added as instances under §"Adopted scaffolds" with their own frozen parity surfaces.

## The vocabulary problem this contract closes

[CLAUDE.md](../CLAUDE.md) requires sub-to-host (Claude Code is the host) and warns against "temporary languages that go poof" — the failure mode where a register imported as scaffolding ossifies into bedrock vocabulary. OpenSpec speaks **proposal / spec / design-doc / task-checklist**; this experiment speaks **0.0 candidate / 1.0 collector / 2.0 signal / 3.0 orchestration / 4.0 bundle / data point / pointer**. Without an explicit translation boundary, the scaffold's register will leak into foundation files, anti-pattern notes will become harder to enforce, and the chain's own emit will start sounding like the scaffold's emit.

The mitigation in this contract: the scaffold's vocabulary is **contained at the boundary**, never imported into foundation or skill files; every scaffold-emitted artifact is translated into the chain's register (or pointed at, untranslated, with a marker) before any chain-internal program consumes it.

## The parity surface (load-bearing)

At adoption time, the operator writes a **frozen parity surface**: the exhaustive list of capabilities the scaffold provides that the closed chain must reproduce before retirement is permitted. The parity surface is committed once and treated as immutable for the scaffold's lifetime. Anything outside the frozen surface is a **chain-only candidate from day one** — the scaffold may not be used for it, and so retirement does not depend on the chain reproducing it.

A parity surface entry has the shape:

```
{
  "capability_id": "<stable handle>",
  "what_scaffold_does": "<one structural sentence — no register-leakage>",
  "chain_equivalent_when_ready": "<which 1.0/2.0/3.0 component or composition will replace it>",
  "parity_predicate": "<deterministic check — input set X, scaffold emits Y, chain must emit Y' that satisfies predicate P>",
  "evidence_pointer": "<pointer kind=collector that runs the parity check, or null until written>"
}
```

A parity-surface entry whose `parity_predicate` is not deterministic, or whose `chain_equivalent_when_ready` is not nameable in the chain's vocabulary, is rejected at adoption-time. Vague parity ("the chain feels as good as the scaffold") is the failure mode this section exists to prevent.

The frozen parity surface for OpenSpec is committed at `foundations/scaffolds/openspec/parity_surface.json` at adoption-time. Until that file exists with at least one entry, OpenSpec is not adopted.

## The retirement signal

Retirement is a 2.0 signal consultation, mirroring the emission-readiness pattern in [zero-four.md](zero-four.md):

```
retirement_signal.evaluate(scaffold_id) -> (verdict, confidence, evidence_pointers)
where verdict ∈ {retire, keep, regression}
```

- `retire`: every entry in the frozen parity surface has its `evidence_pointer` resolving to a data point whose latest run shows the chain's equivalent satisfies the parity predicate.
- `keep`: at least one parity-surface entry is not yet satisfied by the chain. The scaffold continues. `evidence_pointers` names the unsatisfied entries.
- `regression`: an entry that previously satisfied parity no longer does. The scaffold's retirement is blocked and the regression is logged as a gap.

The signal's "training data" is the set of parity-check data points produced by the parity-collectors. The signal's evaluation is a deterministic walk: if every frozen parity entry has a current `passed` data point, return `retire`; if any entry has no passing data point, return `keep`; if any entry has a passing data point that has since been superseded by a `failed` data point, return `regression`. This is the same shape as the operator-approval signal in [proposal.md](proposal.md) — typed query interface first, signal family upgradable later.

The retirement signal cannot return `retire` without per-entry evidence on disk. The chain does not auto-retire scaffolds.

## Handoff procedure

When the retirement signal returns `retire`:

1. A small, deterministic 1.0 retirement program (separate from any 3.0 routine) writes a **handoff record** at `foundations/scaffolds/{scaffold_id}/handoff.json` enumerating, for each parity-surface entry, the chain component that now provides it.
2. An **overlap window** (length declared at adoption-time, default: one operator-acknowledged round) runs both the scaffold and the chain equivalent in parallel, with a parity-collector recording diffs as data points.
3. If the overlap window completes with no `failed` data points, the scaffold's adoption record is marked `retired`, the scaffold's repo/install is removed from the operator's tooling, and `foundations/scaffolds/{scaffold_id}/` becomes a frozen trace directory (not deleted; rejection and retirement leave the same kind of inspectable history that [proposal.md](proposal.md) requires for proposals).
4. If the overlap window records any `failed` data point, retirement reverts to `keep` status, the regression is added to the parity surface as a chain gap, and the scaffold continues until the regression resolves.

Handoff is append-only: a retired scaffold's record cannot be silently re-adopted. Re-adoption is a new adoption event with a new frozen parity surface.

## Anti-ossification rules

Each rule closes a specific way scaffolds turn permanent.

| Rule | Why |
| --- | --- |
| The parity surface is frozen at adoption. New capabilities the operator wants are chain-only candidates from day one — never added to the parity surface mid-tenancy. | Prevents the surface from growing every time the chain catches up, leaving the chain perpetually behind. |
| Scaffold-emitted artifacts are translated at the boundary into the chain's register before any chain-internal program reads them. The translation step is itself a 1.0 collector. | Prevents register leakage — proposal/design-doc/task-checklist vocabulary stays at the edge, X.0/0.X stays in foundation files. |
| No foundation file may import the scaffold's vocabulary. The translation boundary is one-way (scaffold-out, chain-in). | A foundation that uses the scaffold's terms cannot survive the scaffold's retirement without rewrite — which becomes a reason to never retire. |
| The scaffold's adoption record carries a declared **maximum tenancy** (calendar months from adoption). Tenancy elapsing without retirement is itself a flag for operator review — not auto-retirement, but a forced re-justification. | Open-ended tenancy is how scaffolds become permanent infrastructure. |
| No 4.0 bundle may declare a scaffold-emitted artifact as a load-bearing dependency. Bundle-level dependencies must point at chain components or at sub-4.0 candidate components, never at a tenant. | A 4.0 bundle that depends on a scaffold cannot be re-emitted after retirement; that dependency would block retirement permanently. |
| The retirement signal is consulted at every operator-acknowledged round during tenancy, not only when the operator asks. | Catches the moment parity is reached without requiring the operator to remember to check. |

## Detectable violations

Each must be detectable by a 0.1 program. Any violation here that requires human judgement is a hole in this contract.

| Violation | Detection |
| --- | --- |
| Scaffold is in use but no `foundations/scaffolds/{scaffold_id}/parity_surface.json` exists | File-presence check at scaffold-tool invocation time. |
| Parity-surface entry lacks any of the four required fields | JSON schema validator. |
| Parity-surface entry's `parity_predicate` cannot be parsed as a runnable check | Predicate-parser dry-run; failure means the predicate is prose. |
| Parity-surface entries added or removed after adoption | Append-only history check on `parity_surface.json` (only the initial commit may write entries; later commits add satisfaction evidence, not entries). |
| A 4.0 bundle's manifest names a scaffold-emitted artifact as `load_bearing: true` | Bundle-manifest walker scans for scaffold-namespaced pointers and rejects if marked load-bearing. |
| A foundation file (`foundations/*.md`) imports scaffold vocabulary | Lexical scan over foundation files for the scaffold's reserved terms (committed alongside the adoption record). |
| Scaffold-emitted artifact is consumed by a chain-internal program without the boundary translator | Boundary translator emits a `kind=translation` data point per artifact; absence of the data point on a consumed artifact is the violation. |
| `retirement_signal.evaluate` returns `retire` but no handoff record exists | Cross-file consistency check at the next operator-acknowledged round. |
| Handoff record claims chain-equivalence for an entry whose latest parity-check data point is `failed` | Walker re-resolves the evidence pointer and compares verdict. |
| Tenancy exceeds the declared maximum without an operator re-justification record | Date-arithmetic check on the adoption record. |

## What this contract is NOT

- **Not a license to adopt freely.** Each scaffold requires an explicit adoption event. The contract describes the *shape* of adoption; it does not pre-approve any particular tool.
- **Not a 4.0 grading event.** Adopting or retiring a scaffold does not move the chain up the X.0 axis. The chain's grading is unaffected; only the *path* through the bootstrap changes.
- **Not bedrock.** This file is derived. Future experience may show the parity-surface shape needs more fields, the retirement signal needs more verdicts, or the overlap window needs different semantics. Revise this file when that happens; do not revise the four foundations.
- **Not an OpenSpec endorsement.** The contract is general; OpenSpec is named only because it is the first scaffold the operator is considering. Other scaffolds adopted later carry their own parity surfaces and retire under the same contract.
- **Not a TODO list.** A scaffold's parity surface is not "things the chain should eventually do" — it is the exhaustive frozen list of *what this scaffold replaces*. Chain-only capabilities are tracked elsewhere (gap-collectors, proposals).

## Why this shape

Each constraint closes a specific scaffold-related failure mode (the foundations close primitive-level failures; [proposal.md](proposal.md) closes the 0.0→1.0 promotion path; this contract closes the external-tool-during-bootstrap path):

- **Frozen parity surface** closes *moving the goalposts*. Without freezing, the surface grows every time the chain catches up, and retirement never arrives.
- **Deterministic parity predicates** close *vibes-driven retirement*. Without runnable predicates, "the chain is now as good" is a 0.0 free-write claiming to be a 2.0 signal verdict.
- **Translation boundary** closes *register capture*. Without it, the scaffold's vocabulary becomes the chain's vocabulary, and the chain's emit drifts toward the scaffold's framing rather than the framing in [CLAUDE.md](../CLAUDE.md).
- **Maximum tenancy** closes *infinite politeness*. Without a calendar-anchored re-justification, a scaffold that no longer earns its keep stays out of inertia.
- **Append-only adoption history** closes *quiet re-adoption*. A scaffold that was retired and is silently re-adopted hides what the chain failed at; explicit re-adoption surfaces it.
- **No load-bearing 4.0 dependencies on scaffold output** closes *retirement-blocking*. A 4.0 bundle that depends on a scaffold makes retirement equivalent to breaking a graduated artifact.

Holding all of these at once is what lets a scaffold be useful during bootstrap without becoming bedrock. The chain's job is to grow toward parity. The scaffold's job is to retire when it does.

## Adopted scaffolds

| scaffold_id | Adopted | Status | Parity surface | Maximum tenancy |
| --- | --- | --- | --- | --- |
| `openspec` | (pending operator commit of `foundations/scaffolds/openspec/parity_surface.json`) | not yet adopted | (to be committed) | (to be declared at adoption) |

This table is updated by the same append-only discipline as the rest of the contract: adoption appends a row; status changes append a new row; rows are never edited in place.
