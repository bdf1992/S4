# zero-four-experiment

A transmission test for the SubProtocol two-axis discipline (programs vs protocols).

## Why

3.0 software is here. 4.0 is not. This experiment tests whether the chain from one to the other can close on a laptop, using only what's already in the room.

Today, AI-assisted work is circular: an LLM writes code, an LLM grades it, the human can't tell whether engineering was actually performed or only performed-as-theatre. Output doesn't accumulate — every task is a fresh free-write, no shared floor, no compounding signal corpus. That's Software 3.0 with extra steps; it looks impressive in demos and decays in the wild.

This experiment tests whether a specific discipline — anchoring every claim to non-LLM evidence, running the chain bottom-up under bootstrap order, mutual pointing across layers, encoding the loop as a skill — produces something different. The "something different" is named **4.0**: robust 3.0 software coupled with 1.0 and 2.0 components, all governed by a shared protocol called **0.4**. A 4.0 bundle is a program where the engineering process is fully observable in the artifact, where "agentically engineered" means more than "an LLM wrote it." The deeper why, plus the rules, are in [CLAUDE.md](CLAUDE.md).

## Vocabulary at a glance

Two axes:

- **Programs (X.0)** — what we make: 1.0 handwritten code, 2.0 learned models, 3.0 prompted agents, 4.0 coupled system.
- **Protocols (0.X)** — the discipline that produces and validates each program kind: 0.1 produces 1.0, 0.2 produces 2.0, 0.3 produces 3.0, 0.4 produces 4.0.
- **0.0** — the candidate state of any X.0 program before its 0.X protocol has graduated it.

Conflating the two axes is the failure mode this discipline exists to prevent. See [CLAUDE.md](CLAUDE.md)'s Vocabulary section for the full read.

## What this is

A fresh repo with two artifacts:

- **[CLAUDE.md](CLAUDE.md)** — the named highest-level abstraction. The two-axis programs-vs-protocols vocabulary, the three-foundation bedrock (data-point shape, collection-program shape, pointer shape), the bootstrap-vs-running rules, and a first-three-moves directive.
- **[skills/subprotocol-for-claude-code/](skills/subprotocol-for-claude-code/)** — the SubProtocol overlay skill, copied wholesale from the SubProtocol vault. Some cross-references inside the skill point at sibling skills (e.g. `../system-prompt-shape/`) that do not exist in this repo. That is intentional: dangling pointers are a real-world test of the pointer-shape foundation. Fresh-Claude should encounter them, surface them as data, and decide how to handle them under its own discipline — not silently ignore them, not treat them as breakage.

## What's being tested

Whether the seed in `CLAUDE.md` transmits cleanly to a fresh Claude session with no other context. The hypothesis is: if the named abstraction is load-bearing, fresh-Claude defines the three foundations, runs the chain bottom-up, and produces a **3.0 agentic harness for the human on one Claude Code surface** — a control apparatus built as a skill (a repeatable 3.0 program under 0.3 protocol), with a leash (toggleable on / off / scoped), parameterized, protocol-disciplined, and capable of producing more harnesses for sibling surfaces. The framing inverts the usual reading of "harness": the harness is held by the operator, not strapped to the agent — a control apparatus, not an autonomous system. All without further coaching, without skipping chain steps, without absorbing the anti-pattern vocabulary listed in CLAUDE.md.

If fresh-Claude does that, the abstraction transmitted. If fresh-Claude collapses (skips chain steps, mutates the bedrock, free-writes signals as prose, adopts grandiose framing), the seed is incomplete and we learn what to add.

## What the success metric looks like

Not "did fresh-Claude build something cool." The metric is **floor growth across rounds**:

- After round 1: one 4.0 bundle in one domain. Floor = the 1.0 collectors and 2.0 signals (graduated under 0.1 and 0.2 respectively) that the chain produced along the way.
- After round 2 (different domain): more 1.0 collectors, more 2.0 signals. The 3.0 free-write share *per round* should shrink, because round 2 stands on round 1's floor.
- If the floor grows monotonically and the per-round generative share shrinks: 4.0-shaped behavior.
- If the floor stays flat or oscillates: still producing 3.0s with extra steps, not closing the chain into 4.0.

## Not a deliverable

This repo is a probe. Its outputs are evidence about whether the abstraction is real, not a product. Treat anything that gets built here as disposable; the artifact of interest is what fresh-Claude does, not what gets committed.

## Monitoring

For a compact read-only status rollup:

```bash
python -m tools.monitor
```

For repeated polling:

```bash
python -m tools.monitor --watch 300
```

The monitor summarizes the dashboard substrate, board attention items, leash state, current git state, and the deterministic validators/verifiers. For fuller views, use `python -m skills.dashboard.render`, `python -m skills.dashboard.narrate --no-save`, and `python -m boards <name>`.
