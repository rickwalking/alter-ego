# AE-0375 — Pov prompts: hook candidates, outline, content, caption and rubric

Status: Ready
Tier: T2
Priority: High
Type: Feature
Area: Cross-cutting
Owner: Claude (autonomous worker)
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0371-growth-pov-mode
Kanban Card: TBD
Parent: AE-0371
Created: 2026-10-15
Updated: 2026-10-15

## Goal

Generate POV decks from the owner's thesis: hook candidates, outline, content, caption and rubric checks (roadmap R4).

## Problem

Nothing in the pipeline asks for or uses the owner's opinion; slide 1 is a headline, not a hook.

## Scope

- `carousel_pov/v1/{hook,outline,content,caption}.yaml` + README, with the never-invent rule.
- Mode-aware outline/content/caption generation reading a `ContentModeBrief` from the project; hook candidates stored on outline slide 1.
- `PUT /api/carousels/{id}/hook`; content uses `hook_text` for slide 1.
- Validators `hook_word_limit`, `first_person_missing`, `thesis_not_early`, `news_slides_exceeded` with rule-fires tests.
- Outline review shows and picks hook candidates (i18n + tests).

## Non-Goals

- Layouts and images (AE-0376).
- Autopilot thesis confirmation (AE-0377).

## Acceptance Criteria

- [ ] WHEN a POV outline is generated THE SYSTEM SHALL render `carousel_pov/v1/outline` with the thesis, proof, format and slide count, and attach 5 hook candidates to slide 1.
- [ ] WHEN any `carousel_pov/v1` prompt renders THE SYSTEM SHALL include the rule never to invent opinions, experiences, test results or numbers.
- [ ] WHEN no personal proof is given THE content prompt SHALL tell the model to argue from reasoning, not anecdotes.
- [ ] WHEN the owner saves a hook ≤60 chars and ≤10 words THE SYSTEM SHALL store it and use it as the slide-1 heading; a longer hook SHALL be rejected with 422.
- [ ] WHEN slide 1 of a POV deck has more than 10 words THE validator SHALL emit `hook_word_limit` (blocker).
- [ ] WHEN fewer than 3 slides are in first person, or no thesis word is on slides 1-2 THE validator SHALL emit the warning codes.
- [ ] WHEN a POV caption is built THE SYSTEM SHALL render `carousel_pov/v1/caption` with the hook and the CTA goal.

## Gherkin Scenarios

```gherkin
Feature: POV prompts

  Scenario: Hook candidates on the outline
    Given a POV project with a thesis
    When the outline phase runs
    Then slide 1 carries 5 hook candidates

  Scenario: Owner picks a hook
    Given a POV outline with hook candidates
    When the owner saves the second candidate
    Then the content phase uses it as the slide 1 heading

  Scenario: Hook too long
    When the owner saves a hook of 12 words
    Then the API answers 422

  Scenario: Hook word limit fires
    Given a POV slide 1 heading with 11 words
    When the deck is validated
    Then hook_word_limit is reported

  Scenario: No proof means no anecdotes
    Given a POV project without personal proof
    When the content prompt renders
    Then it tells the model to argue from reasoning and never invent an experience
```

## Delta

### ADDED

- `carousel_pov/v1/{hook,outline,content,caption}.yaml` + README, with the never-invent rule.
- Mode-aware outline/content/caption generation reading a `ContentModeBrief` from the project; hook candidates stored on outline slide 1.
- `PUT /api/carousels/{id}/hook`; content uses `hook_text` for slide 1.
- Validators `hook_word_limit`, `first_person_missing`, `thesis_not_early`, `news_slides_exceeded` with rule-fires tests.
- Outline review shows and picks hook candidates (i18n + tests).

### MODIFIED

- See Scope.

### REMOVED

- None.

## Affected Areas

- Backend: agents/outline_agent.py, content_draft_agent.py, generators, caption builder, presentation validators, carousel routes
- Frontend: outline review hook picker
- Database: none (hook_text from AE-0373)
- API: PUT /api/carousels/{id}/hook
- Tests: unit + `carousel_pov_prompts.feature` + vitest
- Docs: carousel-pipeline SKILL.md routing, content-contracts, critical-rules
- Prompts/LLM: carousel_pov/v1
- Observability: agent_name unchanged
- Deployment: none

## Dependencies

- Blocks: AE-0376, AE-0377
- Blocked by: AE-0374
- Related: AE-0371

## Implementation Plan

1. Gherkin
2. prompts
3. brief source + routing
4. hook endpoint
5. validators
6. frontend picker

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-15 10:00

Ticket written from the architect plan (docs/architecture/instagram-growth-pov-mode.md).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- 2026-10-15: design per ADR-0021 and the architect plan; see the epic AE-0371 Decision Log for cross-cutting decisions.

## Blockers

None.

## Final Summary

Pending.
