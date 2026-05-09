<!-- Issue body template for the symphony lifecycle skill.
     The agent fills this in from the operator's verbal brief before
     invoking `python -m skills.symphony new`. The skill does not
     interpolate this template itself — the agent does, then pipes
     the rendered body to stdin.

     Verbatim guidance for the agent:
     - Brief: 1-2 sentences restating operator intent. Verify
       compression handles before writing to github (per memory:
       feedback_intent_verification_via_restatement.md).
     - Success criteria: checkable bullets, not aspirational prose.
       What does done look like such that a verifier could check it?
     - Out of scope: explicit fences against scope creep.
       Reference debts / issues that are explicitly NOT included.
     - Depends on: issue numbers (`#N`), debt IDs (`D-NNN`),
       file paths the work pivots on. Use markdown links into source.
     - Blast radius: low | medium | high, plus one line on what
       could break if the work goes sideways.
-->

[1-2 sentence operator-intent restatement]

## Success criteria
- [checkable bullet]
- [checkable bullet]

## Out of scope
- [explicit fence]

## Depends on
- [issue / debt / file reference]

## Blast radius
[low | medium | high] — [one-line consequence description]
