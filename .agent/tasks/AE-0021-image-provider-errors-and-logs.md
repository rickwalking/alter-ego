# AE-0021 — Image Provider Error Visibility and Logs

Status: Review
Tier: T2
Priority: High
Type: Bugfix
Area: Backend/Observability
Owner: Unassigned
Agent Lane: architect -> developer -> qa -> release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-08
Updated: 2026-06-08

## Goal

Make image generation failures fully visible in workflow state, persisted records, and structured logs.

## Problem

OpenAI/provider failures can collapse into generic background errors. Users and agents cannot see which slide failed, which model was used, what provider returned, or how to recover.

## Scope

- Preserve OpenAI status code, error type, error code, param, and message.
- Store provider request/response/error metadata in generation records.
- Add structured logs for image generation start, reuse, success, and failure.
- Surface slide-level generation errors in workflow state and UI.
- Make provider/model configuration failures retryable after user/provider changes.

## Non-Goals

- Database model creation; handled by AE-0020.
- Prompt editing UI; handled by AE-0019.
- Rendered artifact validation; handled by AE-0018.

## Acceptance Criteria

- [ ] WHEN OpenAI returns 400 invalid model THE SYSTEM SHALL store provider status, type, code, param, and message.
- [ ] WHEN a slide image fails THE SYSTEM SHALL mark that slide failed in `phase_progress.slides`.
- [ ] WHEN image generation fails THE WORKFLOW SHALL set `phase_status=failed` and a human-readable error.
- [ ] WHEN logs are emitted THE LOGS SHALL include project_id, slide_id, slide_number, provider, model, generation_key, prompt_hash, duration, and output path.
- [ ] WHEN errors are logged THE LOGS SHALL NOT include API keys.
- [ ] WHEN the workflow state endpoint returns failure details THE UI SHALL show what happened and which slide failed.

## Gherkin Scenarios

```gherkin
Feature: Image provider error visibility

  Scenario: OpenAI invalid model is visible
    Given OpenAI returns an invalid model error
    When image generation runs
    Then the workflow state is failed
    And the slide error includes the provider error code and message

  Scenario: Logs include slide-level failure context
    Given image generation fails for slide 3
    When logs are captured
    Then the failure log includes project_id and slide_number
    And the log does not include the API key
```

## Delta

### ADDED

- Typed provider error extraction.
- Structured image generation log events.
- Workflow state error details for image generation.

### MODIFIED

- `backend/src/rag_backend/infrastructure/external/openai_image.py`
- `backend/src/rag_backend/application/services/carousel/nodes/images.py`
- `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py`
- Workflow failed UI if needed.

### REMOVED

None.

## Affected Areas

- Backend: yes
- Frontend: yes
- Database: yes
- API: yes
- Tests: yes
- Docs: no
- Prompts/LLM: no
- Observability: yes
- Deployment: no

## Dependencies

- Blocks: AE-0024
- Blocked by: AE-0019, AE-0020
- Related: AE-0009, AE-0010, `.agent/reports/carousel-generation-recovery-plan.md`

## Implementation Plan

1. Add OpenAI error extraction utility with typed fields.
2. Convert provider errors into workflow-safe summaries and persisted details.
3. Emit structured log events around each image generation attempt.
4. Populate `phase_progress.slides` and workflow error details.
5. Add backend tests for invalid model and logging context.
6. Add UI test coverage if frontend failure card changes.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-08

Ticket created from AE-0017 epic.

Developer implementation expanded OpenAI status-error extraction to include
status, request id, error type, error code, and provider message when available.
The image node now emits structured slide-level failure logs and reuse logs with
project id, slide number, model/style, output path, and error summary without
logging API keys. Failed provider attempts are persisted in
`carousel_image_generations.error_json` with the workflow-safe error message.
Remaining scope: richer structured provider error JSON fields, start/success
timing logs with generation key/prompt hash, and UI failure detail cards.

## Files Touched

backend/src/rag_backend/infrastructure/external/openai_image.py
backend/src/rag_backend/application/services/carousel/nodes/images.py
backend/src/rag_backend/infrastructure/database/models/carousel_image_generation.py

## Test Evidence

`cd backend && uv run ruff check ...` on touched backend files: passed.
`cd backend && uv run pytest tests/unit/application/test_image_nodes.py`: passed as part of focused backend suite.

## QA Report

Pending.

## QA Report

See [.agent/reports/AE-0018-AE-0023.qa.md](../reports/AE-0018-AE-0023.qa.md)

**Status**: Review
**Overall Score**: 60% on AC (3/5 pass)

**Blocker Findings**:
- OpenAI error param field not extracted from response
- Error fields collapsed to flat string instead of structured JSON keys
- Error logs missing 6 of 10 required fields (slide_id, provider, model, generation_key, prompt_hash, duration)

**Warning Findings**: None for AE-0021 scope

## Decision Log

- Store full provider details in authenticated/persisted contexts; keep workflow messages concise.

## Blockers

- `_openai_status_error_detail` does not extract `param` field
- `error_json` stores flat `{"message": str}` instead of structured fields
- Error logs at images.py:263-272 are incomplete

## Final Summary

Working foundation established (phase_status=failed, slide-level failure marking, no API key leakage) but 2/5 AC fail on structured error extraction and log completeness.
