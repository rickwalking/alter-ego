# AE-0499 — Chat persona speaks consistently in first person

Status: Dev Complete
Tier: T2
Priority: Medium
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0499-chat-first-person
Kanban Card: TBD
Created: 2026-10-31
Updated: 2026-10-31

## Goal

The public chat speaks as Pedro, always in the first person, in Portuguese and English.

## Problem

From Pedro's 2026-10-22 dashboard QA triage (item CO-2). The chat system prompt
`alter_ego/v3/system.md` says "You are Pedro Marins. Not an AI assistant.", but
four lines describe Pedro in the third person ("they're Pedro's", "Pedro's CV",
"I just know Pedro's stuff", "Pedro's experience"). The model copies that into
replies: "I just know Pedro's stuff", "his alter ego".

## Scope

- New prompt version `alter_ego/v4/system.md` with every reference in first
  person and an explicit first-person rule; README for v4.
- Prompt id and version as named constants; the agent loads v4.
- Deterministic eval: 20 recorded prompts (PT and EN) with good and bad sample
  replies, a reply checker, and prompt scans. No model call in CI.

## Non-Goals

- Changing v1 to v3 (kept for rollback).
- The carousel persona voice gate (see Related evidence).
- A live eval with real model keys.

## Acceptance Criteria

- [x] AC1 `alter_ego/v4/system.md`: everything about Pedro in first person,
  including the vague answer about how the chat works; explicit rule never to
  refer to Pedro in the third person nor call itself "his alter ego" / "an
  assistant for Pedro" / "o alter ego dele"; answers in the user's language.
  Every other v3 rule kept. README for v4. v1 to v3 untouched.
- [x] AC2 The version is a named constant in the context's constants file and
  points at v4; v3 stays loadable.
- [x] AC3 CI eval without a live LLM: 20 eval prompts as data (PT and EN, with
  "who are you?", "quem é você?", "is this a bot?", "você é um robô?", career
  questions); tests that v4 has no third-person reference to Pedro, that v4 has
  the first-person rule, and a reply checker unit-tested on recorded good and
  bad replies.
- [x] AC4 No regression in the existing alter-ego agent and prompt tests.

## Gherkin Scenarios

See `backend/tests/features/chat_first_person_ae0499.feature`.

```gherkin
Feature: The public chat speaks as Pedro, always in the first person

  Scenario: The v4 prompt has no third-person reference to Pedro
    Given the v4 prompt without its first-person rule section
    When it is scanned for "Pedro's", "he", "his", "him", "ele", "dele" and "his alter ego"
    Then nothing is found

  Scenario: Recorded third-person replies are flagged
    Given the 20 recorded eval cases in Portuguese and English
    When the checker reads each bad reply
    Then every reply is flagged
```

## Delta

### ADDED

- `backend/src/rag_backend/agents/prompts/alter_ego/v4/system.md` and `README.md`.
- `backend/src/rag_backend/domain/constants/alter_ego_prompt.py` (`ALTER_EGO_PROMPT_NAME`, `ALTER_EGO_PROMPT_VERSION`).
- `backend/tests/support/first_person_check.py` and `first_person_patterns.py` (test oracle: deterministic reply and prompt checker; not used in production).
- `backend/tests/fixtures/chat_first_person_eval.yaml` (20 recorded eval cases).
- `backend/tests/features/chat_first_person_ae0499.feature`, `backend/tests/unit/agents/test_chat_first_person_ae0499.py`.

### MODIFIED

- `backend/src/rag_backend/agents/alter_ego_agent.py`: loads `ALTER_EGO_PROMPT_NAME` at `ALTER_EGO_PROMPT_VERSION` (v4) instead of the literal `"v3"`.

### REMOVED

- None.

## Affected Areas

- Backend: chat agent prompt loading.
- Frontend: none.
- Database: none.
- API: none.
- Tests: new unit tests, fixture and test oracle; `test_alter_ego_prompt.py` rule asserts now target `ALTER_EGO_PROMPT_VERSION` (v4), with v3 and v2 rollback-load tests.
- Docs: v4 prompt README.
- Prompts/LLM: new `alter_ego/v4` system prompt.
- Observability: none.
- Deployment: none (prompt ships with the image).

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: carousel persona voice gate (see Related evidence).

## Implementation Plan

1. Copy v3 to v4, rewrite the four third-person lines, add the first-person rule section.
2. Move the prompt id and version to constants; point the agent at v4.
3. Write the feature, the eval fixture, the checker and its tests.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Related evidence

On 2026-10-31 two prod QA carousel runs of the queue validation exercised the
**carousel** persona voice gate: run 1 stalled at the content voice gate (voice
score under 70 after the allowed revisions); run 2 reached a voice score of 70.0
(passing) but was then blocked by the presentation validation. This is the
carousel voice gate, related to persona voice quality in general. It is not the
chat prompt and this ticket does not change it.

## Progress Log

### 2026-10-31

Ticket created. v4 prompt, constants, checker, eval fixture and tests written.
Full `gate-capture.sh backend` at 9937b21f1: 26 pass, 0 fail, 1 skip (mutation, CI only). Moved to Dev Complete.
Review follow-up: pronoun rule limited to the speaker, checker generalised with 8 short recorded leaks and 5 recorded
good replies, checker moved to `backend/tests/support/`, prompt scan pins the two quoted lines instead of skipping the
section, existing prompt tests point at the current version, heading renamed, `<<example>` typo fixed in v4.

## Files Touched

See Delta.

## Test Evidence

See `.agent/reports/AE-0499.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- The prompt stays written to the model in the second person ("you", "your own
  CV"), as v1 to v3 are; the reply wording it asks for is first person ("my CV",
  "my projects", "my blog posts").
- The forbidden phrases are quoted in two lines of the
  `SPEAKING AS YOURSELF (FIRST PERSON ONLY)` section. The tests pin those two
  lines to their exact text and scan every other line, so a new third-person
  line in that section is still caught, and an edited pinned line fails.
- The pronoun rule is about the speaker only: third person about other people
  is allowed, and the checker agrees. Replies are flagged for Pedro (or Pedro
  Marins) as a sentence subject, "o Pedro" + a word (not "Sou o Pedro"),
  "his alter ego" / "his assistant" / "assistente dele", and a reply that
  opens with "He" or "Ele". A pronoun about a named someone else later in a
  reply passes. Bare pronouns anywhere are checked on the prompt only.
- The checker is a test oracle under `backend/tests/support/`; production only
  holds the prompt name and version constants.
- No live-eval script: optional in the ticket, and the checker can be reused by
  one later.

## Blockers

None.

## Final Summary

Pending.
