# AE-0025 — Fix Workflow Resume: Interrupt Checkpoint Corruption

Status: Review
Tier: T1
Priority: Critical
Type: Bugfix
Area: Backend/LangGraph
Owner: Unassigned
Agent Lane: developer -> qa -> release
Branch: fix/workflow-resume-interrupt-corruption
Kanban Card: TBD
Created: 2026-06-08
Updated: 2026-06-08

## Goal

Fix the primary bug causing carousel workflow resume to be stuck at 'research' phase after approve: `mark_resume_in_progress()` calls `aupdate_state()` without `as_node`, clearing the LangGraph interrupt checkpoint and causing `engine.resume()` to take the wrong code path (re-running the node without the approve payload).

## Problem

When a user approves research via `POST /workflow/resume` with `{"action": "approve"}`:
1. `mark_resume_in_progress()` patches the LangGraph checkpoint via `aupdate_state(values)` without `as_node`
2. This **clears pending interrupts** (interrupt count goes from 1 → 0)
3. `engine.resume()` then sees `pending_next=('research',)` and `has_interrupts=False` → takes `ainvoke(None)` path
4. `ainvoke(None)` re-runs the research node, which calls `interrupt()` again → workflow stuck at `research/awaiting_human`
5. The approve payload is never delivered

The 202 response returns immediately with hardcoded `phase_status: "in_progress"`, but `get_state()` unconditionally overrides `phase_status` back to `"awaiting_human"` when interrupts exist, making the state appear unchanged to clients.

### Evidence

- Docker logs show checkpoint write: `phase_status=in_progress`, `branch:to:research=null`, interrupt preserved
- No subsequent checkpoint writes from background resume task
- `stuck_workflow` alerts continue showing this project at `research/awaiting_human`
- Integration test `test_approve_research_returns_202_within_two_seconds` times out waiting for outline

## Scope

- Fix `CarouselWorkflowEngine.update_state()` to pass `as_node` parameter preserving interrupt context
- Fix `mark_resume_in_progress()` to NOT patch LangGraph checkpoint (DB-only update)
- Add `as_node` default to all `update_state` callers (audit required)
- Add resume hardening in `CarouselWorkflowEngine.resume()` for corrupted checkpoint recovery
- Add regression test: start → interrupt → approve → assert phase advances to outline
- **Note**: `get_state()` fix moved to AE-0026 (no overlap)

## Non-Goals

- Changing the 202 response pattern (fire-and-forget background task)
- Changing the LangGraph workflow graph structure
- Fixing other phase gates (outline, content, etc.) — they share the same bug but this fix covers all
- Altering the SSE event model

## Acceptance Criteria

- [ ] WHEN user approves research via /workflow/resume THE SYSTEM SHALL advance current_phase to "outline" or beyond (not remain at "research")
- [ ] WHEN mark_resume_in_progress is called THE SYSTEM SHALL NOT clear LangGraph interrupt state (interrupt count stays 1)
- [ ] WHEN background resume completes THE SYSTEM SHALL publish SSE updates with the new phase
- [ ] WHEN background resume fails with ValueError THE SYSTEM SHALL set phase_status to "failed" and publish error SSE event
- [ ] WHEN update_state is called with pending interrupt THE as_node parameter SHALL default to the interrupted node name
- [ ] AUDIT: all callers of update_state (persist_phase_feedback, assigned_reviewer_id, etc.) SHALL pass correct as_node or use the default
- [ ] REGRESSION: fix failing test_workflow_async_resume::test_approve_research_returns_202_within_two_seconds and test_workflow_lifecycle::test_approve_research_advances_to_outline_gate
- [ ] Revise at research gate completes without checkpoint corruption (same fix class)

## Gherkin Scenarios

```gherkin
Feature: Workflow resume interrupt preservation

  Scenario: Approve research advances to outline
    Given a carousel workflow is paused at the research gate
    And the research interrupt is pending in the LangGraph checkpoint
    When the user sends approve action to /workflow/resume
    Then the background resume task calls engine.resume with the approve payload
    And the workflow advances to the outline phase
    And the interrupt is consumed (not recreated)

  Scenario: Resume preserves interrupt checkpoint
    Given a carousel workflow is paused at the research gate
    When mark_resume_in_progress is called
    Then the LangGraph checkpoint SHALL still have 1 pending interrupt
    And the DB project phase_status SHALL be "in_progress"

  Scenario: Revise at research gate completes without corruption
    Given a carousel workflow is paused at the research gate
    When the user sends revise action with feedback
    And persist_phase_feedback calls update_state
    Then the LangGraph checkpoint SHALL still have 1 pending interrupt
    And the workflow SHALL return to research/awaiting_human

  Scenario: Corrupted checkpoint recovery via resume hardening
    Given a carousel workflow checkpoint has pending_next but no interrupts
    And phase_status is "in_progress" in the checkpoint
    When engine.resume is called with approve payload
    Then the system SHALL use Command(resume=payload) path
    And not ainvoke(None)
```

## Delta

### MODIFIED

- `backend/src/rag_backend/agents/carousel_workflow_engine.py` — `update_state()` gets `as_node` param, `resume()` hardens against corrupted state
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py` — `mark_resume_in_progress()` drops checkpoint patch, only updates DB

### ADDED

- Unit tests for interrupt preservation, `as_node` default, and resume hardening
- Update `seed_workflow_phase` test helper if `as_node` changes affect it

## Affected Areas

- Backend: yes
- Frontend: no
- Database: no (no migrations)
- API: no (same 202 response)
- Tests: yes
- Docs: yes (workflow-resume-failure-analysis.md update)

## Dependencies

## Dependencies

- Blocks: AE-0026 (phase_status observability), AE-0027 (stuck detection)
- Related: AE-0017 (carousel generation recovery epic)
- Audit required: all callers of `update_state` including `persist_phase_feedback`, `assigned_reviewer_id` update, finalize failure handler

## Implementation Plan

1. `CarouselWorkflowEngine.update_state()`: Add optional `as_node` parameter, default to reading `snapshot.next[0]` when available.
2. `mark_resume_in_progress()`: Remove the `await self._orchestrator.update_state(...)` call. Only update DB via `_sync_project_phase` and publish SSE event.
3. `CarouselWorkflowEngine.resume()`: Add safety check — if `pending_next` is set but `has_interrupts` is False and checkpoint `phase_status=="in_progress"`, use `Command(resume=payload)` as recovery path.
4. Audit all `update_state` call sites (persist_phase_feedback, assigned_reviewer_id, etc.) to ensure `as_node` is passed correctly.
5. Fix failing integration tests: test_workflow_async_resume, test_workflow_lifecycle.
6. Add unit tests for interrupt preservation, as_node default, and resume hardening.
7. Update workflow-resume-failure-analysis.md.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed (ruff, mypy)
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (resume when checkpoint is corrupted, resume with no interrupt)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-08

- Bug identified via Docker logs and code analysis
- Confirmed by Cursor Composer 2.5 skeptical review
- Ticket created

## Files Touched

- `backend/src/rag_backend/agents/carousel_workflow_engine.py`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py`
- `backend/tests/` (unit + integration tests)

## Test Evidence

Pending.

## QA Report

See `.agent/reports/AE-0025-AE-0026-AE-0027.qa.md`.

## Decision Log

- Do NOT patch LangGraph checkpoint during `mark_resume_in_progress` — DB-only update is sufficient and avoids interrupt corruption.
- Resume hardening with `Command(resume=payload)` recovery path is defense-in-depth for edge cases.

## Blockers

None.

## Final Summary

Pending.