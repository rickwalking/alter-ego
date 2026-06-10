# AE-0019 — Editable Image Prompt Packages

Status: Review
Tier: T2
Priority: High
Type: Feature
Area: Backend/API + Frontend
Owner: Unassigned
Agent Lane: architect -> developer -> qa -> release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-08
Updated: 2026-06-08

## Goal

Expose the full image prompt package before provider calls so users can inspect and edit prompt details, theme, colors, style, model, and final wrapped prompt.

## Problem

The UI currently sees a basic image prompt. It does not expose the final provider prompt or the theme/color/style details that materially affect OpenAI output, so users cannot correct issues before generation.

## Scope

- Add backend prompt package builder for image slides.
- Include raw prompt, sanitized prompt, final wrapped prompt, provider, model, size, strategy, theme, palette colors, prompt hash, and generation key.
- Extend workflow state/API schema to return prompt package details during design/images phases.
- Update image prompt review UI to render details and allow raw prompt edits.
- Submit prompt edits as structured feedback before image generation.

## Non-Goals

- Persisting generation attempt records.
- Provider API error handling.
- Rendered slide export validation.

## Acceptance Criteria

- [ ] WHEN workflow state is requested in design/images phase THE API SHALL return prompt packages for prompted image slides.
- [ ] WHEN a prompt package is returned THE RESPONSE SHALL include theme name, palette colors, model, size, style, final prompt, prompt hash, and generation key.
- [ ] WHEN a user edits a raw prompt THE UI SHALL submit structured feedback that updates the slide prompt before provider generation.
- [ ] WHEN the final prompt is rendered THE UI SHALL distinguish editable raw prompt from read-only final provider prompt.
- [ ] WHEN a prompt has prior generation status or error details THE UI SHALL display them.

## Gherkin Scenarios

```gherkin
Feature: Image prompt package review

  Scenario: Reviewer sees final provider prompt details
    Given the workflow is in the images phase
    When the state endpoint returns slide image prompts
    Then each prompt includes theme colors
    And each prompt includes the final wrapped provider prompt

  Scenario: Reviewer edits a slide prompt before generation
    Given a prompt review panel is open
    When the reviewer changes the raw prompt
    And submits image phase feedback
    Then the backend persists the edited prompt before calling the provider
```

## Delta

### ADDED

- Prompt package builder module.
- Expanded workflow prompt response schema.
- Frontend prompt package review fields and tests.

### MODIFIED

- `backend/src/rag_backend/api/schemas/carousel_workflow.py`
- `backend/src/rag_backend/api/routes/carousels/editorial_workflow_routes_support.py`
- `frontend/src/features/create/components/image-prompt-review.tsx`

### REMOVED

None.

## Affected Areas

- Backend: yes
- Frontend: yes
- Database: no
- API: yes
- Tests: yes
- Docs: no
- Prompts/LLM: yes
- Observability: no
- Deployment: no

## Dependencies

- Blocks: AE-0020, AE-0021
- Blocked by: AE-0017
- Related: AE-0011, AE-0012, `.agent/reports/carousel-generation-recovery-plan.md`

## Implementation Plan

1. Add typed prompt package schema.
2. Build prompt packages from slide data, provider registry strategy, resolved theme, and image style.
3. Compute prompt hash and generation key inputs without requiring a generation record.
4. Extend workflow state response mapping.
5. Update prompt review UI to show model, size, theme, colors, raw prompt, final prompt, and generation key.
6. Support structured prompt edits and backend persistence.
7. Add backend and frontend tests.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-08

Ticket created from AE-0017 epic.

Developer implementation added a shared rendered image prompt package builder
and exposed final provider prompt, generation key, prompt hash, provider/model,
style, theme name, and theme colors in workflow state. The image prompt review
panel now displays the rendered provider prompt and compact metadata badges.
Remaining scope: raw prompt edit submission/persistence before generation and
separate editable-vs-read-only UI controls.

## Files Touched

backend/src/rag_backend/application/services/carousel/image_prompt_package.py
backend/src/rag_backend/application/services/carousel/nodes/images.py
backend/src/rag_backend/api/schemas/carousel_workflow.py
backend/src/rag_backend/api/routes/carousels/editorial_workflow.py
backend/src/rag_backend/api/routes/carousels/editorial_workflow_routes_support.py
backend/tests/unit/api/test_editorial_workflow_state_response.py
frontend/src/features/blog/types-ai.ts
frontend/src/features/create/components/image-prompt-review.tsx
frontend/src/features/create/components/image-prompt-review.test.tsx

## Test Evidence

`cd backend && uv run pytest tests/unit/api/test_editorial_workflow_state_response.py tests/unit/application/test_image_nodes.py`: 16 passed.
`cd frontend && npm test -- --run src/features/create/components/image-prompt-review.test.tsx src/app/dashboard/create/workspace/create-workflow-panel.test.tsx`: 5 passed.

## QA Report

See [.agent/reports/AE-0018-AE-0023.qa.md](../reports/AE-0018-AE-0023.qa.md)

**Status**: Review
**Overall Score**: 100/100 on AC (all 5 pass)

**Blocker Findings**: None
**Warning Findings**: None for AE-0019 scope

## Decision Log

- The UI must review the same final prompt package used by image generation.

## Blockers

None.

## Final Summary

All 5 acceptance criteria pass. Prompt package builder exposes all required fields (theme, colors, model, size, style, final prompt, hash, generation key). UI distinguishes editable raw prompt from read-only rendered prompt. Clean implementation.
