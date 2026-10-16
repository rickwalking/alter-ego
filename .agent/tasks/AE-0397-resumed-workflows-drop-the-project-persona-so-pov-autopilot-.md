# AE-0397 — Resumed workflows drop the project persona, so POV autopilot runs never get a voice score

Status: In Development
Tier: T1
Priority: P0
Type: Bug
Area: backend
Owner: Claude (owner-requested hotfix)
Agent Lane: developer → qa → release
Branch: fix/ae-0397-resume-persona
Kanban Card: TBD
Created: 2026-10-16
Updated: 2026-10-16

## Goal

A content phase reached through a resume is scored with the project's persona, so POV autopilot runs pass the voice gate instead of always escalating.

## Problem

Prod 2026-10-16 (run b241ded5, project 98a2e2f0, persona "Pedro" bound): the run escalated with `persona_not_scored` at the content gate. `editorial_workflow_resume_runner._run_phase` passed `persona=None` on every resume. Only the first `start` carries the persona, and every gate after research is reached through a resume (each autopilot approval, each HTTP revise). The content phase therefore never scored the voice, and every POV autopilot run escalated.

## Scope

- `modules/editorial/infrastructure/pov_inputs.py`: `PovInputsAcl.project_persona(project_id)` reads the persona bound to the project (None when the project has none or the persona was deleted).
- New `application/services/carousel/resume_persona.py`: `load_project_persona(db, project_id)` calls it through the editorial facade (the application layer may not import infrastructure).
- The resume runner passes that persona to `resume_workflow`.

## Non-Goals

- Changing the voice gate threshold or the scoring itself.

## Acceptance Criteria

- [x] AC1: A resume passes the project's persona to the resumed phase.
- [x] AC2: A project without a persona (or a deleted one) resumes without one, as before.

## Gherkin Scenarios

`backend/tests/features/resume_persona_ae0397.feature` (4 scenarios).

## Delta

### ADDED

- `resume_persona.py`, `test_resume_persona_ae0397.py`, `resume_persona_ae0397.feature`

### MODIFIED

- `editorial_workflow_resume_runner.py` (one import, one argument)
- `modules/editorial/infrastructure/pov_inputs.py` (`project_persona`)
- `tests/integration/test_pov_inputs_acl.py` (project persona: bound, none, unknown project)
- `test_editorial_workflow_resume_runner.py` (new pass-through test; an autouse fixture keeps the existing tests on no persona), `test_editorial_workflow_redrive_ae0363.py`

### REMOVED

- None.

## Affected Areas

- Backend: carousel workflow resume
- Frontend: none
- Database: none
- API: none
- Tests: unit + feature
- Docs: this ticket
- Prompts/LLM: persona scoring now runs on resumed content phases
- Observability: none
- Deployment: none

## Dependencies

- Blocks: POV autopilot runs passing the content gate
- Blocked by: none
- Related: AE-0371 (POV voice gate), AE-0373

## Implementation Plan

1. Load the project's persona in the resume runner.
2. Unit tests, plus a negative control.

## QA Checklist

- [x] Security reviewed (read-only lookup by project id)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested (no project, no persona, deleted persona)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-16 09:40

Root-caused from the prod run's state and code; fixed. Negative control: with `persona=None` restored, the new test fails.

## Files Touched

See Delta.

## Test Evidence

- Unit suite: 3976 passed, 0 failed.
- Integration (Postgres, `-k "resume or phase_traces or autopilot or redrive"`): 167 passed; `test_pov_inputs_acl.py` 13 passed.
- Static gates (changed-only): GATES_JSON {"pass":17,"fail":0,"skip":5}.

## QA Report

Pending (hotfix fast path: CI Test & Coverage decides).

## Decision Log

- 2026-10-16: Load the persona from the project row (what the project was created with) rather than threading it through every resume caller.

## Blockers

None.

## Final Summary

Pending.
