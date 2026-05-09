<!-- Issue body template for the symphony lifecycle skill.

     The agent fills this in from the operator's verbal brief before
     invoking `python -m skills.symphony new`. The skill does not
     interpolate this template itself — the agent does, then pipes
     the rendered body to stdin.

     CRITICAL: author at outcome level, not task level.
     Per memory: feedback_outcome_authoring_not_task_authoring.md.
     The operator's review surface is the Acceptance walkthrough
     (filled in by the spawned agent at completion), not the success
     criteria's task list.

     Verbatim guidance for the agent:

     - Outcome: 1-2 sentences restating the operator's intent as an
       observable outcome ("verifier 19/19 green," "X surface no longer
       does Y"), NOT as a task list ("add foo; refactor bar;").

     - Success criteria: checkable bullets framed as state assertions,
       not actions. Right: "data_point.py provenance shape conforms
       to PROV-DM; debts/D-001.json is closed_paid." Wrong: "install
       prov-python; rewrite the provenance schema; update D-001."
       The verifier (or the operator at acceptance time) checks state,
       not actions.

     - Out of scope: explicit fences against scope creep. Reference
       debts/issues/files NOT included.

     - Depends on: prerequisite issues (#N), debts (D-NNN), files.

     - Blast radius: low | medium | high + one-line consequence.

     - Acceptance walkthrough: leave this section empty for the agent
       to fill at completion. The agent's job is to demonstrate the
       outcome here — verifier output, before/after of visible state,
       success criteria checked one by one. The operator reads THIS to
       decide approve/reject. They do not read the diff or the commit
       journey.
-->

[1-2 sentence outcome restatement — what's true after this lands, not what gets done]

## Success criteria
- [state assertion — what is true at the end]
- [state assertion — verifier output, file existence, behavior contract]

## Out of scope
- [explicit fence]

## Depends on
- [issue #N / debt D-NNN / file path]

## Blast radius
[low | medium | high] — [one-line consequence]

## Acceptance walkthrough

_To be filled by the spawned agent at completion. Demonstrate the outcome — paste verifier output, show before/after of measurable state, check each success criterion against ground truth. This is the operator's review surface; do not narrate steps._
