# zero-four-experiment

A transmission test for the SubProtocol ladder discipline.

## What this is

A fresh repo with two artifacts:

- **[CLAUDE.md](CLAUDE.md)** — the named highest-level abstraction. The 0.0–0.4 software-regime vocabulary, the three-foundation bedrock (data-point shape, collection-program shape, pointer shape), the bootstrap-vs-running rules, and a first-three-moves directive.
- **[skills/subprotocol-for-claude-code/](skills/subprotocol-for-claude-code/)** — the SubProtocol overlay skill, copied wholesale from the SubProtocol vault. Some cross-references inside the skill point at sibling skills (e.g. `../system-prompt-shape/`) that do not exist in this repo. That is intentional: dangling pointers are a real-world test of the pointer-shape foundation. Fresh-Claude should encounter them, surface them as data, and decide how to handle them under its own discipline — not silently ignore them, not treat them as breakage.

## What's being tested

Whether the seed in `CLAUDE.md` transmits cleanly to a fresh Claude session with no other context. The hypothesis is: if the named abstraction is load-bearing, fresh-Claude defines the three foundations, builds the ladder bottom-up, and produces a 0.4 program in one small concrete domain — without further coaching, without skipping rungs, without absorbing the anti-pattern vocabulary listed in CLAUDE.md.

If fresh-Claude does that, the abstraction transmitted. If fresh-Claude collapses (skips rungs, mutates the bedrock, free-writes signals as prose, adopts grandiose framing), the seed is incomplete and we learn what to add.

## What the success metric looks like

Not "did fresh-Claude build something cool." The metric is **floor growth across rounds**:

- After round 1: one 0.4 program in one domain. Floor = the 0.1 collectors and 0.2 datasets that the ladder produced along the way.
- After round 2 (different domain): more 0.1 collectors, more 0.2 datasets. The 0.3 free-write share *per round* should shrink, because round 2 stands on round 1's floor.
- If the floor grows monotonically and the per-round generative share shrinks: 0.4-shaped behavior.
- If the floor stays flat or oscillates: still in 0.3 with extra steps.

## Not a deliverable

This repo is a probe. Its outputs are evidence about whether the abstraction is real, not a product. Treat anything that gets built here as disposable; the artifact of interest is what fresh-Claude does, not what gets committed.
