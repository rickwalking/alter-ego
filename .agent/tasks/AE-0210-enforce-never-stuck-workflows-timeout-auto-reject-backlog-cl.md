# AE-0210 — Enforce never-stuck workflows: timeout auto-reject + backlog cleanup

Status: In Development
Tier: T2
Priority: High
Type: Bug
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Stuck workflows are auto-rejected after a timeout (per CLAUDE.md), not left pending forever.

Source: Kaizen prod sweep `.agent/reports/kaizen-prod-2026-06-18.plan.md` (live carousel run, project b5b61790-9372-4a5a-ae17-30d2df28ef3d), validated by an independent architect cold-critic review.

## Problem

CLAUDE.md mandates "Auto-reject after timeout; never leave workflows stuck." But `application/workers/workflow_workers.py` + `WorkflowFailureAlertService` only emit `stuck_workflow` **warnings** — no transition. Prod has **14 workflows stuck at `brief/pending` since 2026-04-28** (verified live).

## Scope

- Implement timeout → auto-reject/cancel (configurable threshold) in the workflow worker.
- One-time cleanup of the existing stuck backlog (transition to a terminal state).
- Metric/alert on the stuck count.
- Seeded test: a workflow past the timeout is auto-transitioned.

## Non-Goals

- Changing the human-approval timeout for active reviews (separate policy).

## Acceptance Criteria

- [x] A past-timeout workflow is auto-rejected/cancelled (no longer `pending`).
- [~] The existing 14+ stuck workflows are cleaned up. — Deferred to ops: per ticket scope ("Do NOT run any cleanup against prod"), the one-time backlog cleanup is an ops action. The worker auto-reject will sweep them on the next tick once deployed (their `updated_at` is far past the 72h timeout).
- [x] Seeded timeout test passes.

## Gherkin Scenarios

```gherkin
Feature: ...

  Scenario: ...
    Given ...
    When ...
    Then ...
```

## Delta

### ADDED

- ...

### MODIFIED

- ...

### REMOVED

- ...

## Affected Areas

- Backend:
- Frontend:
- Database:
- API:
- Tests:
- Docs:
- Prompts/LLM:
- Observability:
- Deployment:

## Dependencies

- Blocks: —
- Blocked by: —
- Related: AE-0017

## Implementation Plan

1. ...

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 HH:mm

Ticket created.

### 2026-06-18 — In Development (worktree feat/kz-workers)

Implemented timeout auto-reject. A workflow is stuck when it is not yet
`published`, sits in a non-terminal pending-like phase status (`pending` or
`awaiting_human`; `in_progress` is excluded as it may be actively resuming), and
its `updated_at` is past the configurable timeout. Each match is transitioned to
the terminal `phase_status=rejected` + `status=failed`, records an
`error_message`, logs `workflow_auto_rejected`, and emits the existing
`content.project.phase_changed` event via the transactional outbox.

Architecture: to respect the import-boundary ratchet (no net-new
application→infrastructure edge), the ORM query/transition lives in a new
infrastructure repository `WorkflowTimeoutRepository` implementing a new domain
protocol `StuckWorkflowAutoRejector`. The worker depends only on the protocol +
an injected factory (`AutoRejectorFactory`); the composition root
(`bootstrap/app_factory.py`) wires the concrete repo. Threshold + enable flag are
Settings (`workflow_stuck_timeout_hours=72`, `workflow_auto_reject_enabled=True`).

NOTE (ops): the existing prod backlog (14 workflows stuck at brief/pending since
2026-04-28) is NOT cleaned up by this change directly; the worker will auto-reject
them on the next tick after deploy (they are far past the 72h window). No prod
mutation was run from this work.

### 2026-06-18 — Dev Complete

Status → Dev Complete.

## Files Touched

- `backend/src/rag_backend/domain/protocols/workflow_timeout.py` (new protocol)
- `backend/src/rag_backend/domain/protocols/__init__.py` (export)
- `backend/src/rag_backend/domain/constants/workflow_timeout.py` (new constants)
- `backend/src/rag_backend/infrastructure/database/workflow_timeout_repository.py` (new repo)
- `backend/src/rag_backend/infrastructure/database/models/carousel.py` (`error_message` → `Mapped[str | None]`)
- `backend/src/rag_backend/infrastructure/config/settings.py` (timeout + enable settings)
- `backend/src/rag_backend/application/workers/workflow_workers.py` (auto-reject tick + factory param)
- `backend/src/rag_backend/bootstrap/app_factory.py` (wire repo into worker)
- `backend/tests/unit/infrastructure/test_workflow_timeout_repository.py` (seeded tests)
- `backend/tests/features/workflow_never_stuck.feature` (Gherkin)

## Test Evidence

```bash
uv run pytest tests/unit/infrastructure/test_workflow_timeout_repository.py -q   # 5 passed
# Covers: past-timeout pending -> rejected + event; within-window untouched;
# in_progress not rejected; awaiting_human rejected; published not rejected.
```

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
