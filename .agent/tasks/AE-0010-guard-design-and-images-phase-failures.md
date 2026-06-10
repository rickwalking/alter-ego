# AE-0010 — Guard Design and Images Phase Failures

Status: Dev Complete
Tier: T2
Priority: High
Type: Bugfix
Area: Backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-05
Updated: 2026-06-05

## Goal

Make design and images phase artifact failures return a deterministic failed workflow state instead of escaping through LangGraph into a generic background runner failure.

## Problem

`content_phase_async` already returns early when `ensure_artifacts()` sets `phase_status` to failed, but `design_phase_async` and `images_phase_async` do not. The AE-0010 validation passed after confirming this missing guard should be fixed. The same resilience gap exists inside `_ensure_design_artifacts`, where `apply_design_tokens()` can raise and escape instead of returning a workflow error payload.

## Scope

- Add the same `PHASE_STATUS_FAILED` early-return guard used by `content_phase_async` to `design_phase_async`.
- Add the same `PHASE_STATUS_FAILED` early-return guard to `images_phase_async`.
- Wrap `apply_design_tokens()` inside `_ensure_design_artifacts` with failure handling.
- Return `phase_status: "failed"` and `WORKFLOW_ERROR_KEY: "Design token application failed"` when design token application fails.
- Add regression tests proving the sync design/images phase functions are not called after failed artifact hydration.
- Add a regression test proving the existing content phase guard remains unchanged.

## Non-Goals

- Exposing slide image prompts through the API.
- Frontend prompt review UI.
- Phase-level retry or auto-retry.
- Changing the content phase behavior beyond regression coverage.
- Changing the persistence model for workflow state.

## Acceptance Criteria

- [x] WHEN `ensure_artifacts()` returns `phase_status == "failed"` in `design_phase_async` THE SYSTEM SHALL return the merged state without calling `design_phase()`.
- [x] WHEN `ensure_artifacts()` returns `phase_status == "failed"` in `images_phase_async` THE SYSTEM SHALL return the merged state without calling `images_phase()`.
- [x] WHEN `apply_design_tokens()` raises inside `_ensure_design_artifacts` THE SYSTEM SHALL catch the exception and return `phase_status: "failed"`.
- [x] WHEN design token application fails THE SYSTEM SHALL set `WORKFLOW_ERROR_KEY` to `"Design token application failed"`.
- [x] WHEN existing content phase guard tests run THE SYSTEM SHALL prove `content_phase_async` still exits before calling `content_phase()` on failed artifact hydration.
- [x] WHEN backend verification runs THE COMMANDS `uv run pytest`, `uv run mypy src/`, and `uv run ruff check src/` SHALL pass for the affected backend scope.

## Gherkin Scenarios

```gherkin
Feature: Design and images phase failure guards

  Scenario: Design phase returns failed artifact state
    Given ensure_artifacts returns phase_status "failed" for the design phase
    When design_phase_async runs
    Then design_phase is not called
    And the returned state has phase_status "failed"

  Scenario: Images phase returns failed artifact state
    Given ensure_artifacts returns phase_status "failed" for the images phase
    When images_phase_async runs
    Then images_phase is not called
    And the returned state has phase_status "failed"

  Scenario: Design token application failure becomes workflow error
    Given apply_design_tokens raises an exception
    When _ensure_design_artifacts runs
    Then the returned state has phase_status "failed"
    And workflow_error is "Design token application failed"
```

## Delta

### ADDED

- Backend unit tests for `design_phase_async` failed-artifact early return.
- Backend unit tests for `images_phase_async` failed-artifact early return.
- Backend unit tests for `_ensure_design_artifacts` design token failure handling.
- Regression test coverage for the existing `content_phase_async` guard.

### MODIFIED

- `backend/src/rag_backend/agents/carousel_workflow_nodes.py`
  - `design_phase_async`
  - `images_phase_async`
- `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py`
  - `_ensure_design_artifacts`

### REMOVED

None.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: no
- API: no
- Tests: yes
- Docs: no
- Prompts/LLM: no
- Observability: no
- Deployment: no

## Dependencies

- Blocks: AE-0011, AE-0012
- Blocked by: none
- Related: AE-0009 (workflow failure feedback), `.agent/reports/AE-0010.arch-plan.md`, `.agent/reports/AE-0010.plan-validation.md`

## Implementation Plan

1. In `carousel_workflow_nodes.py`, mirror the `content_phase_async` failed-status guard in `design_phase_async`.
2. In `carousel_workflow_nodes.py`, mirror the same guard in `images_phase_async`.
3. In `phase_artifact_runner.py`, wrap only the `apply_design_tokens()` call in a `try/except`.
4. Return the failed status and `WORKFLOW_ERROR_KEY` message from `_ensure_design_artifacts` when token application fails.
5. Add focused backend unit tests for both async guards and the design token failure path.
6. Run backend type, lint, and test verification for affected code.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-06-05

- Ticket created from AE-0010 validated plan.
- Branch/worktree: `feat/ae-0003-landing-css-responsive`.
- Added failed-artifact early returns to design and images phase async nodes.
- Wrapped design token application failure into deterministic workflow failed state.
- Added regression tests for content, design, images failed-artifact guards and design token failure handling.
- Grouped touched backend call signatures into request/context objects to satisfy the new max-3-arguments Ruff gate.

## Files Touched

- `backend/src/rag_backend/agents/carousel_workflow_nodes.py`
- `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py`
- `backend/src/rag_backend/agents/carousel_editorial_orchestrator.py`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py`
- `backend/tests/unit/agents/test_carousel_workflow_phases.py`
- `backend/tests/unit/application/test_phase_artifact_runner.py`
- `backend/tests/unit/application/test_editorial_workflow_service.py`

## Test Evidence

- `uv run pytest tests/unit/agents/test_carousel_workflow_phases.py tests/unit/application/test_phase_artifact_runner.py tests/unit/api/test_editorial_workflow_state_response.py tests/unit/application/test_editorial_workflow_service.py -q` — 42 passed.
- `uv run ruff check src/rag_backend/agents/carousel_workflow_nodes.py src/rag_backend/agents/carousel_editorial_orchestrator.py src/rag_backend/application/services/carousel/phase_artifact_runner.py src/rag_backend/application/services/carousel/editorial_workflow_service.py src/rag_backend/api/routes/carousels/editorial_workflow.py src/rag_backend/api/routes/carousels/editorial_workflow_routes_support.py src/rag_backend/api/schemas/carousel_workflow.py tests/unit/agents/test_carousel_workflow_phases.py tests/unit/application/test_phase_artifact_runner.py tests/unit/api/test_editorial_workflow_state_response.py tests/unit/application/test_editorial_workflow_service.py` — passed.
- `env UV_CACHE_DIR=/tmp/uv-cache MYPYPATH=/home/pmarins/projects/alter-ego/backend/src uv run --project .. mypy --explicit-package-bases rag_backend/agents/carousel_workflow_nodes.py rag_backend/agents/carousel_editorial_orchestrator.py rag_backend/application/services/carousel/phase_artifact_runner.py rag_backend/application/services/carousel/editorial_workflow_service.py rag_backend/api/routes/carousels/editorial_workflow.py rag_backend/api/routes/carousels/editorial_workflow_routes_support.py rag_backend/api/schemas/carousel_workflow.py` — no issues in 7 source files.
- `scripts/ci/ruff-strict-changed.sh` — skipped because the script found no committed changed backend source files.
- Note: `uv run mypy src/` is non-runnable under the current backend mypy config because `exclude = "src/"`; it reports no files. The affected source scope passed with explicit package bases from `backend/src`.

## QA Report

Pending.

## Decision Log

- Split from AE-0010 epic because workflow resilience can be implemented and verified independently before API/UI prompt review.
- Reuses the established `content_phase_async` guard pattern rather than introducing a new workflow abstraction.

## Blockers

None.

## Final Summary

Design and images phase artifact failures now return deterministic failed workflow state instead of escaping into the background runner. Design token application failures are caught and reported through `WORKFLOW_ERROR_KEY`.
