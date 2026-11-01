---
status: proposed
date: 2026-11-01
decision-makers: Pedro Marins
consulted: Claude (AE-0588)
informed: delivery team
amends: ADR-003
---

# ADR-0030: Budget-bound field rewrites use a forbidden-phrase check and a voice rescore instead of `PersonaAgent.enforce()`

## Context and Problem Statement

ADR-003 and the root `CLAUDE.md` Persona Engine rule say all AI-generated content must pass
through `PersonaAgent.enforce()`. `enforce()` is a free rewrite of the whole text into the
owner's voice: it has no notion of a character, line or word limit.

Two carousel steps rewrite single slide fields under a hard limit from the presentation
contract:

- the copy-budget shorten step (AE-0588), which runs before the presentation validation and
  shortens every field over its budget with the fast model;
- the content-gate field repair (AE-0430), which runs after a blocked content gate and rewrites
  only the failing fields within their exact limits.

Passing their output through `enforce()` would undo the very limit the rewrite exists to meet
(prod QA run, 2026-11-01: generated copy was 25-40% over budget on several slides), and the
slide would block again at the gate. How do these two steps keep the owner's voice without
`enforce()`?

## Decision Drivers

- Pedro's decision (2026-11-01): generated copy must fit the slide budgets by itself; validators
  and thresholds are never loosened.
- Forbidden phrases are blockers, not suggestions (ADR-003).
- The voice match score must stay at or above 70 before human review.
- No extra model call where a deterministic check is enough.

## Considered Options

1. Run `enforce()` on every rewritten field, then re-check the limit.
2. Exempt the two steps from `enforce()` and replace it with a deterministic forbidden-phrase
   check plus a voice rescore (chosen).
3. Skip any persona control on the rewritten fields.

## Decision Outcome

Chosen option: **2**, as an amendment to ADR-003 scoped to these two budget-bound field
rewrites only. Every other AI-generated content keeps going through `enforce()`.

- The rewrite prompt carries the owner's style guide (`PersonaAgent.style_guide()`), including
  the forbidden phrases.
- The shorten step rejects, in code, any answer that adds a forbidden phrase the current text
  did not have; a rejected answer leaves the field unchanged.
- After the shorten step, the persona voice of the slides whose copy changed is scored again
  (unchanged slides keep their score by text fingerprint). A shortened slide whose voice score
  falls below `VOICE_MATCH_MIN_SCORE` (70) while its previous score met it goes back to its
  previous copy and score, with no extra model call; the over-budget copy then reaches the
  normal validation.
- The content-gate field repair keeps its existing behavior (style guide in the prompt); the
  persona voice gate still judges its result before approval.

### Consequences

- Good: the limits the rewrite meets are not undone; the voice floor and the forbidden-phrase
  rule are still enforced, deterministically where possible.
- Good: no extra `enforce()` call per rewritten field; one judge call per changed slide.
- Bad: the rewritten field is not restyled by `enforce()`; voice drift under the floor is caught
  only by the rescore, not prevented.
- Neutral: the Persona Engine rule text in `CLAUDE.md` is unchanged until this ADR is accepted.

### Confirmation

- `backend/tests/unit/application/test_copy_budget_fit_ae0588.py`: a rewrite with a forbidden
  phrase is rejected.
- `backend/tests/unit/application/test_content_budget_step_ae0588.py`: changed slides are
  rescored; a slide dropping under 70 is reverted with no extra model call.

## More Information

- ADR-003: Implement Persona-Driven AI Content (amended by this ADR once accepted).
- Ticket: `.agent/tasks/AE-0588-copy-fits-slide-budgets.md`.
