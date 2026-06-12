# AE-0046 — Validation Refactor for ContentSlideCopy

Status: In Development
Tier: T2
Priority: Medium
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa
Branch: feat/ae-0046-validation-contentslidecopy
Kanban Card: AE-0046
Created: 2026-06-10
Updated: 2026-06-10

## Goal

Replace the 40-line `_validate_selected_structured_field` method in `ContentSlideCopy` with a dispatch-based validator pattern (`_VALIDATORS` dict). Eliminate the "if hell" that makes the model fragile to new `content_kind` values.

## Problem

PR #11 comment on `carousel_presentation.py`: "This is a if hell. So many inner if statements. This is not manageable, this will cause a lot of issues to tests." The `_validate_selected_structured_field` method has 3 mutually exclusive branches (features/stats/insight), each with complex field validation logic. Adding a new `content_kind` requires modifying this method.

## Scope

- Define `ContentKindValidationContext` TypedDict
- Extract validator functions: `_validate_features_content(ctx)`, `_validate_stats_content(ctx)`, `_validate_insight_content(ctx)`
- Create `_VALIDATORS: dict[str, ContentKindValidator]` dispatch table
- `_validate_selected_structured_field` becomes ~5 lines
- Also extract `_validate_lucide_icon_name` into a shared mixin or module-level function (currently duplicated in 4 model classes)

## Non-Goals

- Changing the Pydantic model fields or their types
- Refactoring other validators in the same file
- Adding new content_kind values

## Modularization Alignment (2026-06-12)

Wave B (after AE-0041) — pre-builds target architecture. Per the plan,
`ContentSlideCopy` validation **belongs to the carousel_presentation
domain** (Phase 5):

- The `_VALIDATORS` dispatch and `ContentKindValidationContext` stay
  module-local to the presentation models.
- The shared `_validate_lucide_icon_name` extraction must live inside
  the presentation models package (module-level function), NOT in a
  global shared/validation module — the plan forbids shared-kernel
  dumping grounds.
- Pure validation functions with no vendor imports — Phase 5 then moves
  files, not logic.

## Acceptance Criteria

- [ ] 3 independent validator functions created, each tested in isolation
- [ ] `_VALIDATORS` dispatch dict with `"features"`, `"stats"`, `"insight"` entries
- [ ] `_validate_selected_structured_field` reduced to <= 10 lines
- [ ] `_validate_lucide_icon_name` not duplicated across model classes (extracted to module level)
- [ ] All existing tests pass without modification
- [ ] Mutation testing: 80%+ mutation score on new validators
- [ ] Adding a new content_kind requires only: a new validator function + new entry in `_VALIDATORS`

## Gherkin Scenarios

```gherkin
Feature: Dispatch-Based Validation

  Scenario: features validator catches missing features
    Given content_kind "features" and features=None
    When ContentSlideCopy is validated
    Then ValueError is raised with ERR_FEATURES_REQUIRED

  Scenario: features validator catches forbidden stats
    Given content_kind "features" and stats is not None
    When ContentSlideCopy is validated
    Then ValueError is raised with ERR_FEATURES_FORBIDDEN_FIELDS

  Scenario: insight validator succeeds
    Given content_kind "insight" with valid insight data
    When ContentSlideCopy is validated
    Then validation passes

  Scenario: unknown content_kind
    Given content_kind "bogus"
    When ContentSlideCopy is validated
    Then no ValueError is raised (unknown kinds pass through)
```

## Delta

### MODIFIED

- `domain/models/carousel_presentation.py`

### ADDED

- `ContentKindValidationContext` TypedDict
- `_validate_features_content`, `_validate_stats_content`, `_validate_insight_content`
- `_VALIDATORS` dispatch dict
- Unit test file for validators

## Affected Areas

- Backend: Domain model
- Tests: Unit tests in `tests/unit/domain/`
- Docs: None
- Observability: None

## Dependencies

- Blocks: None
- Blocked by: AE-0041 (may reference new constants)
- Related: None

## Implementation Plan

1. Define `ContentKindValidationContext` TypedDict
2. Extract `_validate_features_content` with all features validation logic
3. Extract `_validate_stats_content` with all stats validation logic
4. Extract `_validate_insight_content` with all insight validation logic
5. Create `_VALIDATORS` dict
6. Replace the `model_validator` body with a dict lookup + delegate call
7. Extract `_validate_lucide_icon_name` to module level, remove duplicates
8. Write mutation-killing tests
9. Run `ruff check` + `mypy strict`

## QA Checklist

- [ ] Acceptance criteria validated
- [ ] Edge cases tested — null features, empty lists, wrong types
- [ ] Mutation score >= 80%

## Progress Log

### 2026-06-10

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
