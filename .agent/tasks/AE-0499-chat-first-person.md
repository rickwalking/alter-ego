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
- `backend/src/rag_backend/domain/constants/alter_ego_voice.py` (prompt id, version, checker patterns).
- `backend/src/rag_backend/agents/first_person_check.py` (deterministic reply and prompt checker).
- `backend/tests/fixtures/chat_first_person_eval.yaml` (20 recorded eval cases).
- `backend/tests/features/chat_first_person_ae0499.feature`, `backend/tests/unit/agents/test_chat_first_person_ae0499.py`.

### MODIFIED

- `backend/src/rag_backend/agents/alter_ego_agent.py`: loads `ALTER_EGO_PROMPT_AGENT` at `ALTER_EGO_PROMPT_VERSION` (v4) instead of the literal `"v3"`.

### REMOVED

- None.

## Affected Areas

- Backend: chat agent prompt loading.
- Frontend: none.
- Database: none.
- API: none.
- Tests: new unit tests and fixture.
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
- The forbidden third-person phrases are quoted only inside the
  `SPEAKING AS ME (FIRST PERSON ONLY)` section; the prompt scan skips that
  section and checks the rest of the prompt, bare pronouns included.
- The reply checker only flags patterns anchored on Pedro or on the
  "alter ego / assistant" self-description, so a reply that says "he" about
  someone else (a former manager) is not flagged. Bare pronouns are checked on
  the prompt only.
- No live-eval script: optional in the ticket, and the checker can be reused by
  one later.

## Blockers

None.

## Final Summary

Pending.
