# AE-0009 — Frontend Workflow Error Feedback & Retry

Status: Review
Tier: T2
Priority: High
Type: Feature
Area: Frontend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-05
Updated: 2026-06-05

## Goal

Improve frontend error feedback when an editorial workflow phase fails (e.g., "Invalid JSON response from LLM" in content drafting), and add a retry mechanism to restart the workflow from scratch.

## Problem

When a workflow phase fails mid-execution (phase_status: "failed"), the user sees a generic error `NeonAlert` on the workspace page but has no actionable recovery path:

1. The workspace page shows the error in a `NeonAlert` with `variant="destructive"` but no retry button
2. The publish page shows `awaitingFinalApproval` indefinitely — the phase_status is `failed` but there's no indication of what went wrong or how to retry
3. `isWorkflowReady()` returns `true` for `failed` status, so the approve button becomes clickable, but approving a failed state proceeds with corrupted content
4. The only existing "retry" is in `handleStartWorkflow()` which resets `workflowStarted=false`, letting the user click Start again — but this only handles *start* failures, not mid-workflow phase failures

## Scope

### Backend
- Persist `error_message` in the workflow state when a phase fails (captured from LLM/phase error)
- Add `error_message?: string` field to `EditorialWorkflowState` API response

### Frontend
- Detect `phase_status === "failed"` in the workspace and publish pages
- Show a prominent error card with:
  - Which phase failed (current_phase)
  - The persistent error message from backend workflow state (`workflowState.error_message`)
  - A "Retry Workflow" button that restarts the workflow
- In the publish page, replace "awaitingFinalApproval" with the error card when workflow has failed
- Add sidebar failure badge — show "(failed)" next to current phase in sidebar
- Add i18n keys for the retry UI
- Ensure retry is disabled while in-flight (prevents double-click)
- Tighten `EditorialWorkflowState.phase_status` type to use `(typeof WORKFLOW_PHASE_STATUS)[keyof ...]`
- Add unit tests for the new error state rendering

## Non-Goals

- Phase-level retry (resuming from the failed phase rather than full restart) — backend doesn't support this
- Auto-retry — user must click the button (no automatic retry loop)
- Modifying the resume/approve flow when phase_status is failed
- Changing `isWorkflowReady()` behavior

## Modularization Alignment (2026-06-12)

Product feature (not debt) — schedule freely, with two compatibility
rules from the modularization plan:

- `error_message` on the workflow state response must be **additive and
  optional** — response-schema stability is a standing migration
  invariant, and AE-0076 freezes SSE event names (additive payload
  fields are allowed; renames are not).
- The `phase_status` type tightening should use the glossary's status
  families once AE-0071 lands (`phase_status` vs `build_status` vs
  `review_status` vs `publication_status`); if this ships first, keep
  current literals and note the follow-up.
- Retry semantics must be idempotent (duplicate retry clicks → one
  restart): this previews the plan's concurrency contract (AE-0073) —
  reference it in the implementation.

## Acceptance Criteria

### Backend
- [ ] `error_message` field persisted in workflow state when a phase fails
- [ ] `EditorialWorkflowState` API response includes `error_message?: string`
- [ ] Error message survives page refresh (loaded from workflow state, not SSE ephemeral)

### Frontend
- [ ] Workspace page shows a prominent error card when `phase_status === "failed"`
- [ ] Error card displays which phase failed (e.g., "Content drafting failed")
- [ ] Error card displays the backend error message from `workflowState.error_message`
- [ ] Error card persists across page refresh (loaded from persisted workflow state)
- [ ] Sidebar shows "(failed)" badge next to current phase when `phase_status === "failed"`
- [ ] "Retry Workflow" button is shown in the error card
- [ ] Retry button calls `start()` with the project's existing topic/audience/brief/sources
- [ ] Retry button is disabled while the retry request is in-flight
- [ ] On retry success, workflow progress UI resumes normally
- [ ] On retry failure, error remains visible (button re-enables)
- [ ] Publish page shows error card instead of `awaitingFinalApproval` when workflow has failed
- [ ] Starting a fresh workflow (non-failed) shows existing behavior unchanged
- [ ] i18n keys added for: phase failure label, retry button, retrying state
- [ ] `EditorialWorkflowState.phase_status` tightened to use `(typeof WORKFLOW_PHASE_STATUS)[keyof ...]`
- [ ] Unit tests cover: error card render, retry button click, retry loading state, retry failure, publish page failed state, error message persistence
- [ ] No TypeScript errors, lint passes, existing 772+ tests pass

## Gherkin Scenarios

```gherkin
Feature: Workflow Error Feedback & Retry

  Scenario: Failed phase shows error card on workspace
    Given the editorial workflow has phase_status "failed"
    And current_phase is "content"
    When the workspace page renders
    Then a prominent error card is displayed
    And the card shows "Content drafting failed"
    And the card shows the backend error message
    And a "Retry Workflow" button is visible

  Scenario: Retry button restarts the workflow
    Given the workflow is in "failed" state
    When the user clicks "Retry Workflow"
    Then the workflow start() is called with the project's inputs
    And the button is disabled while retrying
    And on success, the workspace resumes normal flow

  Scenario: Retry failure keeps error visible
    Given the workflow is in "failed" state
    When the user clicks "Retry Workflow"
    And the start() call fails
    Then the error card remains visible
    And the retry button is re-enabled

  Scenario: Publish page shows failed state
    Given the editorial workflow has phase_status "failed"
    When the publish page renders
    Then the error card is shown instead of "awaitingFinalApproval"
    And a "Back to workspace" link is available

  Scenario: Non-failed workflow shows existing behavior
    Given the editorial workflow is in "in_progress" or "awaiting_human"
    When the pages render
    Then no error card is shown
    And existing behavior is preserved

  Scenario: Error message persists across page refresh
    Given the editorial workflow has phase_status "failed"
    And error_message is stored in the workflow state
    When the user refreshes the page
    Then the error card is still displayed
    And the error message matches the stored error_message

  Scenario: Sidebar shows failure badge
    Given the editorial workflow has phase_status "failed"
    When the sidebar renders
    Then a "(failed)" badge is shown next to the current phase name
```

## Delta

### ADDED

- `WorkflowFailedCard` component in `frontend/src/features/create/components/workflow-failed-card.tsx`
- i18n keys for failed phase display and retry (en.json + pt.json)
- `error_message` field in backend workflow state storage + API response

### MODIFIED

- `frontend/src/app/dashboard/create/[id]/page.tsx` — detect `failed` status, show error card with retry in workspace step
- `frontend/src/app/dashboard/create/[id]/publish/page.tsx` — detect `failed` status, show error card instead of `awaitingFinalApproval`
- `frontend/src/features/create/hooks/use-editorial-workflow.ts` — expose retry function or pass through `start()` for retry
- `frontend/src/constants/editorial-workflow.ts` — add retry-related constants if needed
- `frontend/src/constants/workflow.ts` — no changes needed (FAILED constant exists)
- `frontend/src/features/blog/types-ai.ts` — tighten `phase_status` type, add `error_message`
- `frontend/src/app/dashboard/create/workspace/create-workspace-sidebar.tsx` — add failure badge indicator
- `frontend/src/i18n/locales/en.json` + `pt.json` — add new i18n keys
- **Backend**: workflow state handling — persist `error_message` when a phase fails

### REMOVED

None.

## Affected Areas

- Backend: yes (workflow state persistence — add `error_message` field)
- Frontend: yes
- Database: no (error_message stored in JSONB workflow state, no migration needed)
- API: yes (EditorialWorkflowState response includes `error_message`)
- Tests: yes (new unit tests for error card component + backend persistence)
- Docs: no
- Prompts/LLM: no
- Observability: no
- Deployment: no

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0008 (URL source extraction may reduce failures, but retry is still needed for other LLM errors)

## Implementation Plan

### 1. Backend: Persist `error_message` in workflow state

- In `backend/src/rag_backend/agents/carousel_workflow_nodes.py` (or wherever phases catch errors), when a phase sets `phase_status: "failed"`, also capture the error message and store it as `error_message` in the shared workflow state dict
- In `backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py`, ensure `error_message` is returned in the state response if present
- Verify the field survives `GET /state` (it lives in JSONB, so minimal change)

### 2. Frontend: Update types

- In `frontend/src/features/blog/types-ai.ts`:
  - Tighten `phase_status: string` to `phase_status: (typeof WORKFLOW_PHASE_STATUS)[keyof typeof WORKFLOW_PHASE_STATUS]`
  - Add `error_message?: string` field

### 3. Frontend: Create `WorkflowFailedCard` component

- In `frontend/src/features/create/components/workflow-failed-card.tsx`:
  - Props: `currentPhase`, `errorMessage`, `onRetry`, `isRetrying`
  - Shows phase name mapped to human-readable label via i18n
  - Shows error message from `workflowState.error_message`
  - Shows "Retry Workflow" button (disabled when `isRetrying`)

### 4. Frontend: Add i18n keys

- In `en.json` + `pt.json`:
  - `editorialWorkflow.failed.phaseLabel: "{phase} failed"` (with phase name interpolation)
  - `editorialWorkflow.failed.retryButton: "Retry Workflow"`
  - `editorialWorkflow.failed.retrying: "Restarting workflow..."`
  - `editorialWorkflow.failed.goBack: "← Back to workspace"` (for publish page)

### 5. Frontend: Update workspace page

- In `frontend/src/app/dashboard/create/[id]/page.tsx`:
  - Check `editorialWorkflow.state?.phase_status === WORKFLOW_PHASE_STATUS.FAILED`
  - If failed, show `WorkflowFailedCard` with retry wired to `handleStartWorkflow`
  - Pass existing project topic/audience/brief/sources from `project` data

### 6. Frontend: Update publish page

- In `frontend/src/app/dashboard/create/[id]/publish/page.tsx`:
  - After the `awaitingFinalApproval` block, add: if `workflowState?.phase_status === WORKFLOW_PHASE_STATUS.FAILED`, show error card
  - Show the failed phase, error message, and a "Back to workspace" link

### 7. Frontend: Add sidebar failure badge

- In `frontend/src/app/dashboard/create/workspace/create-workspace-sidebar.tsx`:
  - When `phase_status === "failed"`, append "(failed)" to the current phase label

### 8. Run typecheck + lint + tests

- `cd frontend && npm run typecheck && npm run lint && npm run test`
- `cd backend && uv run mypy src/ && uv run ruff check src/ && uv run pytest`

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-06-05

Ticket created.

## Files Touched

- backend: editorial_workflow_routes_response.py, workflow_state_fields.py, +8 builder tests
- frontend: app/dashboard/create/[id]/page.tsx, features/blog/types-ai.ts, +2 test files
  (failed-card/publish/sidebar/i18n/hook pre-existed in base)

## Test Evidence

```
frontend: typecheck clean, lint clean, 816 passed (73 files)
backend: mypy Success (389), ruff clean, 1659 passed, 2 skipped
```

## QA Report

✅ PASS — Product batch QA (Cursor), WARN→fix→confirmation PASS. See `.agent/reports/AE-0009.qa.md` → `.agent/reports/product-ae0008-ae0009.qa.md`.Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
