# AE-0011 — Expose Slide Image Prompts in Workflow State

Status: Dev Complete
Tier: T2
Priority: High
Type: Feature
Area: Backend/API
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-05
Updated: 2026-06-05

## Goal

Expose persisted per-slide image prompts in the editorial workflow state response during design and images phases so the frontend can show meaningful content for review.

## Problem

The backend already stores image prompts on slide records, but the workflow state API does not return them. During the design approval gate the user sees a generic "Design applied" state without the prompt content that will drive image generation. The AE-0010 validation explicitly accepted the route-handler approach: fetch slides in the route handler, pass them into the response builder, and avoid wiring database access into the builder itself.

## Scope

- Add a `SlideImagePrompt` response schema with `slide_index`, `title`, and `image_prompt`.
- Add `slide_image_prompts: list[SlideImagePrompt] | None` to `EditorialWorkflowStateResponse`.
- Update `build_workflow_state_response()` to accept optional slide records supplied by the route handler.
- Populate `slide_image_prompts` only when `current_phase` is `design` or `images`.
- Return `slide_image_prompts = None` for all other phases or when slide records are unavailable.
- Skip slide records with empty or null `image_prompt`.
- Fetch current slide records in `GET /carousels/{id}/workflow/state` through the existing carousel repository path and pass them into the builder.
- Add backend tests for phase gating, field mapping, empty prompts, and graceful degradation.

## Non-Goals

- Frontend rendering of prompts.
- Editing or saving prompt changes.
- Adding prompt fields to workflow state storage.
- Database migrations.
- Changing image generation behavior.

## Acceptance Criteria

- [x] WHEN `EditorialWorkflowStateResponse` is serialized THE SYSTEM SHALL include `slide_image_prompts: list[SlideImagePrompt] | None`.
- [x] WHEN the current phase is `design` and slide records have prompts THE SYSTEM SHALL populate `slide_image_prompts`.
- [x] WHEN the current phase is `images` and slide records have prompts THE SYSTEM SHALL populate `slide_image_prompts`.
- [x] WHEN the current phase is any non-design/images phase THE SYSTEM SHALL set `slide_image_prompts` to `None`.
- [x] WHEN prompt records are mapped THE SYSTEM SHALL preserve each slide record's `slide_index`, `title`, and `image_prompt`.
- [x] WHEN a slide record has an empty or null `image_prompt` THE SYSTEM SHALL skip that slide in `slide_image_prompts`.
- [x] WHEN the builder receives no slide records THE SYSTEM SHALL set `slide_image_prompts` to `None` without raising.
- [x] WHEN the route cannot fetch slide records THE API SHALL still return the workflow state with `slide_image_prompts` set to `None`.
- [x] WHEN backend verification runs THE COMMANDS `uv run pytest`, `uv run mypy src/`, and `uv run ruff check src/` SHALL pass for the affected backend scope.

## Gherkin Scenarios

```gherkin
Feature: Slide image prompts in workflow state

  Scenario: Design phase returns prompt records
    Given the workflow current_phase is "design"
    And the project has slide records with image prompts
    When the workflow state endpoint is requested
    Then slide_image_prompts contains one item per prompted slide
    And each item includes slide_index, title, and image_prompt

  Scenario: Non-review phases omit prompt records
    Given the workflow current_phase is "content"
    And the project has slide records with image prompts
    When the workflow state response is built
    Then slide_image_prompts is null

  Scenario: Slide query failure degrades gracefully
    Given the workflow current_phase is "images"
    And loading slide records fails
    When the workflow state endpoint is requested
    Then the endpoint still returns the workflow state
    And slide_image_prompts is null
```

## Delta

### ADDED

- `SlideImagePrompt` schema in `backend/src/rag_backend/api/schemas/carousel_workflow.py`.
- Backend unit tests for prompt response mapping and phase gating.
- Backend route/builder tests for graceful degradation when slides are unavailable.

### MODIFIED

- `backend/src/rag_backend/api/schemas/carousel_workflow.py`
  - `EditorialWorkflowStateResponse`
- `backend/src/rag_backend/api/routes/carousels/editorial_workflow_routes_support.py`
  - `build_workflow_state_response()`
- `GET /carousels/{id}/workflow/state` route handler
  - Fetch slide records and pass them to the response builder.

### REMOVED

None.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: no
- API: yes
- Tests: yes
- Docs: no
- Prompts/LLM: no
- Observability: no
- Deployment: no

## Dependencies

- Blocks: AE-0012
- Blocked by: AE-0010
- Related: `.agent/reports/AE-0010.arch-plan.md`, `.agent/reports/AE-0010.plan-validation.md`

## Implementation Plan

1. Add the `SlideImagePrompt` Pydantic model and optional response field.
2. Extend `build_workflow_state_response()` with an optional `slides` parameter.
3. In the builder, return prompt rows only for `design` and `images` phases.
4. Skip empty prompt values and preserve slide index/title/prompt data exactly.
5. Update the route handler to load slide records via the existing repository path and pass them into the builder.
6. Catch route-side slide loading failures and fall back to `slides=None`.
7. Add tests for populated prompts, non-review phases, empty prompts, no slides, and slide query failure.
8. Run backend type, lint, and test verification for affected code.

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
- Added `SlideImagePrompt` API schema and optional `slide_image_prompts` workflow state response field.
- Extended workflow state response building with route-supplied slide records.
- Added design/images phase gating, empty prompt filtering, exact prompt preservation, and no-slides fallback.
- Added route-side slide loading with graceful degradation when the repository fetch fails.
- Grouped route dependencies/build inputs into Pydantic context models to satisfy the max-3-arguments Ruff gate.

## Files Touched

- `backend/src/rag_backend/api/schemas/carousel_workflow.py`
- `backend/src/rag_backend/api/routes/carousels/editorial_workflow.py`
- `backend/src/rag_backend/api/routes/carousels/editorial_workflow_routes_support.py`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py`
- `backend/tests/unit/api/test_editorial_workflow_state_response.py`
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

- Keep database access in the route handler and pass slide records into the response builder, matching the validation resolution.
- Do not add prompt fields to workflow state storage because prompt records already exist in persisted slide data.

## Blockers

None.

## Final Summary

Workflow state responses now expose persisted slide image prompts during design and images phases, while non-review phases and slide-load failures degrade to `slide_image_prompts = None`.
