# AE-0421 — A re-driven phase drafts and scores with the project persona

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Claude (orchestrator)
Branch: fix/ae-0421-redrive-persona
Created: 2026-10-18
Updated: 2026-10-18

## Goal

When the autopilot re-drives a parked phase (AE-0363), the phase runs with the project's persona,
exactly like a resume (AE-0397), so content is drafted in the creator's voice and voice-scored.

## Problem

2026-10-18, pov_news carousels 519c7b57 (run 5b5701a6) and 901e51bb (run 790e8969): after the LLM
outage both runs had content re-driven (`autopilot_runner_redrive`). Both content passes produced
no `persona_scores` and escalated with `persona_not_scored`; the drafts also scored low (20–70)
when judged afterwards. There were zero `persona_judge_failed` events, so scoring never ran.

Cause: `EditorialWorkflowService.redrive_pending_phase` builds
`EditorialWorkflowStartInput(topic="", audience="", brief="", sources=[], user_id="")` with no
persona, and the resume runner's re-drive branch never loads one. The content node then drafts
with `persona=None` and `_score_content_drafts` returns `{}` when the persona is missing. Carousels
reaching content through a normal resume (persona loaded, AE-0397) were scored normally.

## Scope

- `redrive_pending_phase(project_id, db, persona=None)` passes the persona into the start input.
- The resume runner's re-drive branch loads it with `resume_persona.load_project_persona`.

## Non-Goals

- Re-running content for the two affected carousels (handled operationally).

## Acceptance Criteria

- [x] A re-drive loads the project's persona.
- [x] The re-run node's workflow input carries that persona.
- [x] A project without a persona still re-drives (persona None).

## Gherkin

`backend/tests/features/redrive_persona_ae0421.feature`.

## Repro Steps

1. Park a pov_news carousel before content (outline approved), then let the runner re-drive it.
2. Content runs with no persona: no `persona_scores`, run escalates `persona_not_scored`.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

AE-0363 (re-drive), AE-0397 (resume persona).

## Progress Log

### 2026-10-18 14:15

Ticket created; persona passed through the re-drive; tests.

## Files Touched

- backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py
- backend/src/rag_backend/application/services/carousel/editorial_workflow_resume_runner.py
- backend/tests/unit/application/test_editorial_workflow_redrive_ae0363.py
- backend/tests/features/redrive_persona_ae0421.feature

## Test Evidence

Pending (hotfix fast path gates).

## QA Report

Pending.

## Blockers

None.
