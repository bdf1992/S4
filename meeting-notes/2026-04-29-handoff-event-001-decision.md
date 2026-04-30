# Handoff — Event 001 decision pending

**Created:** 2026-04-29 (session end).
**Status:** the repo is between sessions, working tree clean, verify green at 19/19. One open decision is parked: how (or whether) to execute Event 001 — the foundation-grounding refactor logged in [foundations/grading-events.md](../foundations/grading-events.md). This file is what fresh-Claude reads first on resume.

This file is a **citation**, not a data point. It captures session-end state in prose; if it diverges from the actual repo, trust source and `git log` over this file. Every claim made here is verifiable by the commands in §6.

---

## 1. What this repo is

A transmission test for SubProtocol's ladder discipline; full framing is in [README.md](../README.md) and [CLAUDE.md](../CLAUDE.md). The deliverable is an **agentic leash for Claude Code**: a skill ([skills/leash_for_hooks/](../skills/leash_for_hooks/)) that walks the bedrock ladder bottom-up (0.1 collectors → 0.2 signals → 0.3 orchestration) for one Claude Code harness surface (`settings.json/hooks`) and emits a verifiable bundle. Floor-growth across rounds — sibling leashes reusing shared bedrock — is the success metric, not "first 0.4 bundle."

## 2. Current state

| Thing | Where | Last-known value (verify with §6 commands) |
| --- | --- | --- |
| Foundations | [foundations/](../foundations/) | 4 files, all hardcoded immutable: `data-point.md`, `collection-program.md`, `pointer.md`, `zero-four.md` |
| Foundation changelog | [foundations/grading-events.md](../foundations/grading-events.md) | Event 001 PENDING — operator decision required before any foundation file is touched |
| Working leash | [skills/leash_for_hooks/](../skills/leash_for_hooks/) | Surface: `settings.json/hooks`. 4 collectors, 3 resolvers, 2 signals, 1 orchestration entry, 1 verify walker, 1 toggle (`leash_state.json`) |
| Verify | `python -m skills.leash_for_hooks.verify` | 19 self-checks, 0 failures, exit 0 |
| Last emitted bundle | `skills/leash_for_hooks/outputs/run-<hash>/` | gitignored / regenerable; last claim was `candidate` (emission-readiness gate `not_ready` because `0 < MIN_EXEMPLARS=50` promoted exemplars) |
| Operator toggle | [skills/leash_for_hooks/leash_state.json](../skills/leash_for_hooks/leash_state.json) | The operator changes this between sessions — `cat` it; do not trust this handoff's snapshot |
| Datasets (collector outputs) | `skills/leash_for_hooks/datasets/` | gitignored / regenerable; last counts: 14 LLM-SDK denylist entries, 29 hook events, 0 hook configs, 0 promoted exemplars |
| Promoted exemplars | [skills/leash_for_hooks/exemplars/promoted/](../skills/leash_for_hooks/exemplars/promoted/) | Empty by design — operator hasn't promoted any yet; gate stays `not_ready` until ≥50 |
| Sibling leashes | `skills/leash_for_slash_commands/` (in-progress, **uncommitted** at handoff time) | Operator has begun the second leash; check `git status` and `ls skills/` to see current state. [recursion-seam.md](../skills/leash_for_hooks/recursion-seam.md) is the spec the sibling is being built against. |

## 3. What's parked: Event 001

The operator pushed back during session 2026-04-29 that the bedrock's shapes (data-point provenance, value_schemas, audit budgets) were synthesized from CLAUDE.md without anchoring to published standards. Two research agents were dispatched; ground-truth findings:

- Authored `provenance` shape → should map to **W3C PROV-DM** (PROV-JSON serialization, no RDF stack required).
- Ad-hoc `VALUE_SCHEMA = {...}` dicts that nothing actually validates → should be **Pydantic v2** models exporting **JSON Schema Draft 2020-12**.
- "audit budget ≤ 80 LOC" pure invention → should be **cyclomatic complexity ≤ 10** (McCabe 1976; NIST SP 500-235; Pylint/Ruff/Radon defaults).
- No `pyproject.toml` → add at repo root per **PEP 518 + PEP 621**.

Per CLAUDE.md ("foundations are immutable; changes are 0.4 grading events; log explicitly"), the gap was logged as Event 001 PENDING and **no foundation file was modified**. Two branches are written up in detail in [foundations/grading-events.md](../foundations/grading-events.md) under Event 001:

- **Plan A** (approve, execute): 10 staged commits. Adds `pyproject.toml`, refactors `lib/data_point.py` to PROV-JSON + Pydantic-validated values, refactors `lib/audit.py` to use radon, then rewrites the four affected foundation .md files in turn citing the standards. ~4-6h, medium-high risk. Verify will fail repeatedly during; needs to be rolled forward step by step.
- **Plan B** (reject, close out): 1 commit. Stamps each affected foundation with an "un-grounding disclosure" block and marks Event 001 REJECTED with re-trigger conditions. ~30min, zero risk.

Refinements to either are possible (e.g., "Plan A minus the cyclomatic refactor"). The full plans are in `grading-events.md`.

## 4. The operator's working pattern (observed across this session)

This is intentional context for fresh-Claude — adapt to it.

- **Parallel edits.** The operator edits files in real time during the agent session (saw: `MIN_EXEMPLARS = 3` → `50`, `leash_state.json` cycling on/off/scoped, `lib/leash_state.py` created mid-stream, recursion-seam.md updates committed in parallel). **Always re-read before committing**; the file may have changed since the last tool call.
- **Steering via narrator-console.** [meeting-notes/narrator-console.md](narrator-console.md) lists explicit operator commands ("Read the floor", "Show the fence", "Run the gate", "Point to the receipt", "Name the next thin spot", "Spawn the sibling") and a watch-point rubric. The most binding line is on the Bedrock row: *"Stop unless this is explicitly a 0.4 grading event."* That's why Event 001 was logged but not executed.
- **Citations vs data points.** [meeting-notes/](.) is for citation-tier captures (meeting transcripts, this handoff, narrator notes). They're explicitly NOT Foundation-1 data points. Don't try to dress them up as such; don't try to demote real data points to citations. The distinction is load-bearing.
- **Pushback is honest signal, not friction.** When the operator pushes back ("I want to second-guess your formatting and organization patterns"), the right move is to investigate (research agents, WebFetch the actual specs) and log the gap, not to defend the existing implementation.
- **"Go" means execute the immediately-prior proposal**, not "execute everything you might think of." When the operator said "go" after the research-agents-vs-refactor question, that meant "do the research"; the refactor still needed approval.
- **Auto mode is active** but is not authorization to skip orientation or to mutate bedrock. Even in auto mode: re-read source first, ask before destructive or hard-to-reverse work.

## 5. What NOT to do (hard rules)

- **Don't touch any file in [foundations/](../foundations/) except [grading-events.md](../foundations/grading-events.md)** without operator approval. The bedrock spec files are immutable; modifying them requires a logged 0.4 grading event AND explicit operator sign-off. Event 001 is logged; operator approval is what's pending.
- **Don't fabricate exemplars** to make `emission_readiness` fire `ready`. The empty `exemplars/promoted/` is honest; faking it produces a 0.4 claim sitting on theatre, which is exactly what the foundations were written to prevent.
- **Don't claim `0.4`** on a candidate bundle. Verify enforces this; respect it.
- **Don't add `Co-Authored-By: Claude...` trailers** to commits — the environment hook rejects them as fabricated attribution. See `.../memory/feedback_no_coauthor_trailer.md`.
- **Don't refactor for "cleanliness"** without a 0.2 signal saying it's worth the cost. Floor-growth is the metric, not surface tidiness.
- **Don't preemptively spawn a sibling leash.** [narrator-console.md](narrator-console.md) cue: *"Build the second leash surface only after deciding which surface matters most."* — *but note*: as of this handoff, the operator has begun an in-progress sibling at `skills/leash_for_slash_commands/` (uncommitted). Re-read the operator's actual work before applying this rule; the operator's running code overrides the agent's prior caution.
- **Don't use the `Skill` tool to invoke leash-for-hooks** mid-session — it's a CLI tool you run via `python -m skills.leash_for_hooks.{orchestrate,verify}`. The Anthropic Skill spec doesn't have shell-script invocation; this skill is a hybrid (CLI for now; SKILL.md frontmatter conforms to the spec for discovery purposes).

## 6. Verify-on-resume checklist

Run these to confirm this handoff still matches reality. If any of them disagree with this file, trust the command and update this file (or write a new dated handoff).

```sh
# Branch and recent commits — confirm we're on master and the commit
# graph still ends at the SHAs this handoff was written under
git log --oneline -10
# Last 5 commits at handoff write time:
#   d831b26 ground bedrock against published specs (round 1: leash-bundle level)
#   fe53d14 recursion-seam: align seam #6 with the actual Skill spec
#   971b8cc recursion-seam: extend to cover the toggle (leash_state.json + lib/leash_state.py)
#   8e2d945 leash toggle: operator-authored on/off/scoped state, wired into orchestrate + verify
#   106b5c0 move 3: tighten emission_readiness threshold to 50 exemplars

# Verify state — should be 19/19, exit 0
python -m skills.leash_for_hooks.verify

# Working tree — should be clean
git status

# Operator toggle — read the actual file; do not trust the snapshot in §2
cat skills/leash_for_hooks/leash_state.json

# Event 001 status line — should still be PENDING
grep -E "^\*\*Status:\*\*" foundations/grading-events.md
```

## 7. First action on resume

1. Run the §6 checklist. Reconcile any drift.
2. Re-read the operator's most recent uncommitted file edits (if any) — they're signal about where the operator's attention has moved since this handoff.
3. Greet the operator with a one-sentence status and **ask the Event 001 question directly**: *"Event 001 is still PENDING — Plan A (execute the foundation grounding, ~10 commits, citations) or Plan B (close out as REJECTED with un-grounding disclosure, 1 commit)? Or refine?"*
4. Don't propose adjacent work until the Event 001 decision is made; the operator will redirect if needed.

## 8. Things in flight that aren't blocking

These are noted in case they become relevant; none of them block the Event 001 decision.

- The `hook_config` collector currently extracts `{event, matcher, hook_index, command, command_hash}` per hook — but the published Claude Code hook schema has 5 hook types (`command`, `http`, `mcp_tool`, `prompt`, `agent`) and several common fields (`if`, `timeout`, `statusMessage`, `once`) the collector ignores. Enriching it is a leash-bundle-only change (no foundation touch) but introduces breaking schema changes for any consumer. Reasonable to defer until the hook_config dataset is non-empty (someone actually configures hooks on this machine).
- The "lift `lib/` to a top-level shared `bedrock/` package" refactor is documented in [recursion-seam.md](../skills/leash_for_hooks/recursion-seam.md) as a v0.2 move, appropriate to do once a second leash exists. **Now appropriate** — the operator has begun `skills/leash_for_slash_commands/`. Lifting `lib/` after the sibling stabilizes is the natural next step; doing it before the sibling stabilizes is premature.
- A cross-leash registry (so `verify.py` can detect two leashes claiming the same surface) becomes appropriate as soon as the sibling leash commits. With one leash, premature; with two, useful.
- An additional in-flight meeting note ([2026-04-29-receipts-and-existing-structure.md](2026-04-29-receipts-and-existing-structure.md)) is **uncommitted** at handoff time — alignment work on file-shape, receipts, and accounting framing. Read it for vocabulary/orientation; nothing in it requires immediate code action.
- The `narrator-console.md` is a meta-layer; if it accretes use across sessions it may eventually become its own skill. For now it's deliberate citation-tier prose.
