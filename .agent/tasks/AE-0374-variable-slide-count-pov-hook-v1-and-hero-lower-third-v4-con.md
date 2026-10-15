# AE-0374 — Variable slide count: pov_hook_v1 and hero_lower_third_v4 contracts

Status: Dev Complete
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Claude (autonomous worker)
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0371-growth-pov-mode
Kanban Card: TBD
Parent: AE-0371
Created: 2026-10-15
Updated: 2026-10-15

## Goal

Let a presentation contract declare a slide-count range and per-slide roles (roadmap R3).

## Problem

Every deck is 7 slides: the loader knows one fixed sequence, `MAX_SLIDES = 7`, and the outline normalizer forces the 7 canonical types by position and drops unknown keys.

## Scope

- `contracts/pov_hook_v1.yaml` (8-10 slides, roles, POV copy budgets, POV rubric) and `contracts/hero_lower_third_v4.yaml` (Radar IA roles, optional 8th twist, no artwork on summary/closing).
- Loader: optional `slide_count_min/max`, `role`, `optional`; validation that roles are known and the range is consistent; `expand_policy_for_count`.
- `MAX_SLIDES` 7 → 10 with `LEGACY_SLIDE_COUNT = 7`; role-aware outline normalizer; deck-level `slide_count_invalid`; policy chosen per project (mode → contract).
- New Radar IA projects stamped v4, POV projects stamped `pov_hook_v1`.

## Non-Goals

- Changing v1-v3 contracts.
- Prompts (AE-0375).

## Acceptance Criteria

- [x] WHEN a contract has no range keys THE loader SHALL behave as today (min = max = slide_count).
- [x] WHEN `pov_hook_v1` is expanded for 8, 9 or 10 slides THE SYSTEM SHALL keep 2, 3 or 4 point slides and renumber the sequence.
- [x] WHEN a contract declares an unknown role or min > max THE loader SHALL fail with `presentation_policy_invalid`.
- [x] WHEN every outline slide carries a known role THE normalizer SHALL keep the roles and map each to its slide type, up to 10 slides; otherwise it SHALL apply the legacy 7-slide positional normalization unchanged.
- [x] WHEN an outline length is outside the contract range THE validator SHALL emit `slide_count_invalid` (blocker).
- [x] WHEN a carousel is created THE SYSTEM SHALL stamp `pov_hook_v1` for POV and `hero_lower_third_v4` for Radar IA.

## Gherkin Scenarios

```gherkin
Feature: Variable slide count

  Scenario Outline: POV deck sizes
    Given the pov_hook_v1 contract
    When it is expanded for <slides> slides
    Then it has <points> point slides and the last three roles are twist, save, cta

    Examples:
      | slides | points |
      | 8      | 2      |
      | 9      | 3      |
      | 10     | 4      |

  Scenario: Legacy outline unchanged
    Given an outline without roles
    When it is normalized
    Then it is trimmed to 7 slides with the canonical slide types

  Scenario: Outline too long
    Given a pov project expecting 8 to 10 slides
    When its outline has 11 slides
    Then slide_count_invalid is reported as a blocker
```

## Delta

### ADDED

- `contracts/pov_hook_v1.yaml` (8-10 slides, roles, POV copy budgets, POV rubric) and `contracts/hero_lower_third_v4.yaml` (Radar IA roles, optional 8th twist, no artwork on summary/closing).
- Loader: optional `slide_count_min/max`, `role`, `optional`; validation that roles are known and the range is consistent; `expand_policy_for_count`.
- `MAX_SLIDES` 7 → 10 with `LEGACY_SLIDE_COUNT = 7`; role-aware outline normalizer; deck-level `slide_count_invalid`; policy chosen per project (mode → contract).
- New Radar IA projects stamped v4, POV projects stamped `pov_hook_v1`.

### MODIFIED

- See Scope.

### REMOVED

- None.

## Affected Areas

- Backend: presentation_policy*, outline_normalize, types.py, crud/editorial_driver
- Frontend: none
- Database: none
- API: none
- Tests: unit + `carousel_variable_slide_count.feature`
- Docs: contracts/README.md
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0375, AE-0376
- Blocked by: AE-0373
- Related: AE-0371

## Implementation Plan

1. Gherkin
2. contracts
3. loader + expansion
4. normalizer + MAX_SLIDES
5. deck check
6. stamping

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-15 10:00

Ticket written from the architect plan (docs/architecture/instagram-growth-pov-mode.md).

### 2026-10-15 (dev)

Implemented in eb31476, 33a0884 on `feat/ae-0371-growth-pov-mode`. Ready for the final relay round.

## Files Touched

`pov_hook_v1.yaml`, `hero_lower_third_v4.yaml`, policy loader ranges/roles, `expand_policy_for_count`, `project_policy`, role-aware normalizer + `stamp_outline_roles`, `slide_count_invalid` deck rule, `MAX_SLIDES` 10, stamping at create, tests + `carousel_variable_slide_count.feature`.

## Test Evidence

Static gates 16/16 PASS on `33a0884`; full `tests/unit` re-run green after updating 5 tests that pinned the 7-slide/v3 behaviour.

Gate details and GATES_JSON: `.agent/reports/AE-0374.dev-summary.md` and the epic summary `.agent/reports/AE-0371.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- 2026-10-15: design per ADR-0021 and the architect plan; see the epic AE-0371 Decision Log for cross-cutting decisions.

## Blockers

None.

## Final Summary

Pending.
