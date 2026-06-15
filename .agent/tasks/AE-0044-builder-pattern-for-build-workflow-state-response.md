# AE-0044 — Builder Pattern for build_workflow_state_response

Status: Review
Tier: T2
Priority: Medium
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: architect → developer → qa
Branch: feat/ae-0044-builder-workflow-state-response
Kanban Card: AE-0044
Created: 2026-06-10
Updated: 2026-06-10

## Goal

Refactor `build_workflow_state_response` using a Field Descriptor Mapping pattern (lightweight Builder) to eliminate ~16 repetitions of `str(state.get(...))` / `list(state.get(...) or [])`. Add deprecation wrapper for the old function signature.

## Problem

PR #11 review comment: "very complex function. Let's think about the best architect solution. Maybe a Builder pattern. Create a plan to resolve this." The function has 62 lines, ~16 repeated field-mapping patterns, and each new field requires manual boilerplate.

## Scope

- Extract 5 pure field extractor functions: `_string_field(key)`, `_list_field(key)`, `_int_field(key)`, `_localized_reviews_field(key)`, `_validation_field(key)`
- Define `_FIELD_MAPPING: list[tuple[str, Callable[[dict[str, object]], object]]]` with 12+ entries
- `build_workflow_state_response` reduced to ~5 lines
- Add `@deprecated` wrapper keeping the old function callable for 1 sprint
- Inline `_string_list_map` and `_int_map` helpers into extractors
- Add comprehensive unit tests for each extractor and the full mapping

## Non-Goals

- Changing the `EditorialWorkflowStateResponse` Pydantic model
- Adding new fields to the response
- Refactoring other response builder functions (handled separately)

## Modularization Alignment (2026-06-12)

Wave B (after AE-0041) — pre-builds target architecture. Per the plan's
AE-0040 interaction table, this work **belongs to the editorial inbound
HTTP adapter / response mapping** (Phase 4):

- Keep the field extractors pure and colocated with the route response
  module so Phase 4 lifts the whole unit into
  `modules/editorial/adapters/inbound/http/`.
- `_FIELD_MAPPING` is transport mapping, not domain logic — no imports
  from ORM models or services inside extractors.
- If AE-0071's glossary has landed, use its status-family names in new
  identifiers (`phase_status` etc.); otherwise keep current names and
  leave renames to Phase 4.
- The deprecated old signature is removed per AE-0050's window — before
  Phase 4 starts, so the facade never wraps a deprecated function.

## Acceptance Criteria

- [ ] 5 pure field extractor functions created and unit-tested
- [ ] `_FIELD_MAPPING` defined as module-level constant with 12+ entries
- [ ] `build_workflow_state_response` reduced to <= 10 lines
- [ ] Old function signature kept as `@deprecated` wrapper with `warnings.warn(DeprecationWarning)`
- [ ] All existing tests pass without modification (they call the old name)
- [ ] `mypy strict` passes on modified file
- [ ] Ruff `PLR0913` and `PLR0912` not violated
- [ ] Mutation-killing tests for each extractor (null state, wrong types, all-fields-present)

## Gherkin Scenarios

```gherkin
Feature: Field Descriptor Mapping

  Scenario: build_workflow_state_response with full state
    Given a workflow state dict with all fields populated
    When build_workflow_state_response is called
    Then all 12+ fields match the input values

  Scenario: build_workflow_state_response with empty state
    Given an empty workflow state dict
    When build_workflow_state_response is called
    Then string fields default to ""
    And list fields default to []
    And optional fields default to None

  Scenario: deprecated wrapper
    Given code that imports build_workflow_state_response
    When the refactored version is called
    Then a DeprecationWarning is issued
```

## Delta

### MODIFIED

- `api/routes/carousels/editorial_workflow_routes_response.py`

### ADDED

- 5 extractor functions (`_string_field`, `_list_field`, etc.)
- `_FIELD_MAPPING` constant
- Unit test file for extractors

### REMOVED

- `_string_list_map` and `_int_map` helpers (inlined into extractors)

## Affected Areas

- Backend: API response builder
- Tests: New unit tests in `tests/unit/api/`
- Docs: None
- Observability: None

## Dependencies

- Blocks: None
- Blocked by: AE-0041 (uses `STATE_FIELD_*` constants that AE-0041 creates)
- Related: None

## Implementation Plan

1. Define 5 extractor functions as closures in `editorial_workflow_routes_response.py`
2. Build `_FIELD_MAPPING` list with typed entries
3. Refactor `build_workflow_state_response` to iterate over mapping
4. Add `import warnings` and `@deprecated` wrapper
5. Write unit tests for: null state, full state, wrong types, partial state
6. Run mutation testing on the module
7. Verify `ruff check` and `mypy strict`

## QA Checklist

- [x] Security reviewed — no auth changes
- [x] Code quality reviewed — no `type: ignore`
- [x] Acceptance criteria validated
- [x] Edge cases tested — None values, type mismatches, missing keys
- [x] Orphan/unfinished code checked — old imports still work

## Progress Log

### 2026-06-10

Ticket created.

## Files Touched

- editorial_workflow_routes_response.py (builder+extractors+wrapper)
- editorial_workflow_routes_support.py, editorial_workflow.py (call sites)
- tests/unit/api/test_editorial_workflow_routes_response.py (new, 51 tests)

## Test Evidence

```
mypy strict: Success (389); ruff: clean
pytest: 1648 passed, 2 skipped
golden snapshot: output byte-identical pre/post
```

## QA Report

✅ PASS — Wave 4 batch QA, 2 independent passes both PASS (1 round-1 warning adjudicated false-positive). See `.agent/reports/AE-0044.qa.md` → `.agent/reports/wave-4.qa.md`.

## High Risk Areas

<!-- AE-0050 safeguard tagging — feeds architect-skill skeptical-review trigger -->

- Risk level: **MEDIUM**
- Reason: API response builder change (`build_workflow_state_response` →
  `build_editorial_workflow_state_response`) on the editorial workflow HTTP
  surface still consumed by the open PR #11 workflow.
- Affected high-risk surfaces: carousel workflow (editorial state response),
  event emission (phase progress / status fields surfaced in the response),
  artifact paths (image assets surfaced via the sanitized state).
- Mitigation: typed `@deprecated` wrapper `build_workflow_state_response`
  retained for the AE-0050 migration window (see AE-0050 wrapper inventory).

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
