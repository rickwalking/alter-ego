# AE-0033 — Presentation Validation and Bounded Repair

Status: Review
Tier: T2
Priority: Critical
Type: Feature
Area: Backend/Validation
Owner: Unassigned
Agent Lane: developer -> qa -> release
Branch: feat/ae-0033-presentation-validation
Kanban Card: TBD
Created: 2026-06-09
Updated: 2026-06-09

## Goal

Add deterministic presentation validation and one bounded repair attempt before invalid slide copy can be persisted, approved, refined, rendered, or published.

## Problem

Approval gates currently check persona score but not presentation quality. Invalid capitalization, emoji, dash punctuation, shape drift, repeated headings, drafting labels, over-budget copy, unsupported Lucide names, and empty translations can reach persistence and render.

## Scope

- Add `carousel/presentation_validation.py`.
- Validate after outline, content generation, persona output, reviewer edits, refinement, pre-render, and final artifact health.
- Add stable violation codes.
- Add one repair attempt per locale with bounded timeout.
- Reject invalid Lucide `icon_name` values, emoji, raw SVG, and arbitrary icon strings.
- Update refinement to validate, repair, persist, and rerender atomically.

## Non-Goals

- Browser geometry preflight, which is AE-0036.
- Frontend review UI, which is AE-0034.
- Renderer shell changes, which are AE-0035.

## Acceptance Criteria

- [ ] WHEN visible copy or structural parity is invalid THE SYSTEM SHALL perform at most one bounded repair per locale and SHALL block persistence if the result remains invalid or times out.
- [ ] WHEN English headings start with lowercase cased letters THE SYSTEM SHALL repair from context without title-casing the entire heading.
- [ ] WHEN visible text contains decorative emoji THE SYSTEM SHALL return `visible_emoji_forbidden`.
- [ ] WHEN structured slide markers contain emoji, raw SVG, arbitrary strings, or unsupported Lucide names THE SYSTEM SHALL reject them before persistence.
- [ ] WHEN translation parse fails THE SYSTEM SHALL fail with a stable code and SHALL NOT return `{}`.

## Gherkin Scenarios

```gherkin
Feature: Versioned carousel presentation contract

  Scenario: Invalid English heading is repaired before persistence
    Given an English heading whose first cased letter is lowercase
    When deterministic validation requests its one repair attempt
    Then the repaired heading is revalidated
    And only valid copy is persisted

  Scenario: Invalid copy remains invalid after repair and blocks approval
    Given visible copy violates a blocking rule
    And the one repair attempt still violates that rule
    When the content phase completes
    Then no candidate copy is persisted
    And the phase fails with the stable violation code
```

## Delta

### ADDED

- Presentation validator and stable violation codes.
- Copy repair prompt flow with one attempt per locale.
- Protected-token tests and timeout tests.
- Mutation target for validator branches.

### MODIFIED

- Generation, persona, refinement, approval, render preflight, and health paths.
- Translation parse failure behavior.

### REMOVED

- Silent invalid-copy persistence.
- Silent empty translation fallback.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: yes
- API: yes
- Tests: yes
- Docs: no
- Prompts/LLM: yes
- Observability: yes
- Deployment: no

## Dependencies

- Blocks: AE-0034, AE-0038, AE-0039
- Blocked by: AE-0032
- Related: AE-0031

## Implementation Plan

1. Implement deterministic text, structure, and icon validation.
2. Add stable violation code constants.
3. Add bounded repair prompt and one-attempt orchestration.
4. Integrate validation into generation, persona, refinement, pre-render, and health.
5. Add unit, integration, and mutation-target tests.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-09

Ticket created from AE-0028 architecture plan.

## Files Touched

Pending.

## Test Evidence

```bash
cd backend && uv run pytest tests/unit/application/test_presentation_validation.py tests/unit/application/test_presentation_review.py -q
# 18 passed
```

## QA Report

Pending.

## Decision Log

- Deterministic validators, not OCR, are the primary correctness gate.

## Blockers

Blocked by AE-0032.

## Final Summary

Pending.
