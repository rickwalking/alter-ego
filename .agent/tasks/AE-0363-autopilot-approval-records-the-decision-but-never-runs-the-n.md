# AE-0363 — Autopilot approval records the decision but never runs the next phase

Status: Dev Complete
Tier: T1
Priority: P0
Type: Bugfix
Area: backend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0363-autopilot-resume-runs-phase
Created: 2026-10-14
Updated: 2026-10-14
Parent: AE-0348

## Goal

An autopilot approve or revise runs the next phase for real, with a live run (heartbeat, run
events, epoch fence), and a workflow left with no run in flight is re-driven or escalated,
never parked silently.

## Problem

Prod 2026-10-14, carousel `8e350d6e-78fc-436c-ab95-bed02535198b`, autopilot run
`9e06e958-45b6-4339-bcb2-92981d4e4e7b`. After AE-0362 the run was re-driven to `generating`
and the runner approved the outline gate. Checkpoint afterwards: `content/approved`,
`slide_drafts=0`, `lock_version=5`. Row: `outline/awaiting_human`, `lock_version=5`,
`run_started_at`/`run_heartbeat_at` NULL, `updated_at` 17:36 (before the re-drive). The
policy read `content/approved`, saw a status other than `awaiting_human`, and waited forever.
No exception in the logs. A tick transaction sat "idle in transaction" for minutes right after
`UPDATE carousel_projects SET lock_version=...`.

Root cause (verified in code and reproduced with the real service + graph):

1. The hypothesis "the in-process driver only records the decision and never executes the
   phase" is **wrong**. `InProcessEditorialDriver.resume` → `EditorialService.record_review_decision`
   → `EngineReviewDecisionAdapter` → `EditorialWorkflowService.resume_workflow` →
   `orchestrator.resume` → graph `ainvoke`. The content node DOES run, inside the worker tick.
2. It ran on the tick session with the `lock_version` bump flushed but uncommitted for the
   whole LLM run (the "idle in transaction"), without marking the row `in_progress` (no
   `run_started_at`, no heartbeat, no `run.started`/`run.finished`, no epoch fence).
3. LangGraph's checkpointer commits on its own connection: the outline node's approved
   super-step (`outline_approved=True`, `phase_status=approved`, next=`content`) was committed
   before the content node started.
4. When the content node raised a provider error, `is_provider_outage` matched (it matches every
   `openai.APIError`, including `APITimeoutError` / `APIConnectionError`), the driver rolled the
   tick back and returned `PROVIDER_OUTAGE`, and the runner ignores that status (it only acts on
   `REVISION_CAP`). Nothing is logged. Result: checkpoint parked before the `content` node with no
   interrupt, row rolled back to `outline/awaiting_human`, `lock_version` unchanged — exactly the
   prod signature. `decide()` only acts on `awaiting_human`/`failed`, so it waits forever.
5. Re-sending an `approve` to that checkpoint is a trap: `Command(resume=…)` with no open
   interrupt is a null resume that the content gate's `interrupt()` consumes, so the content
   gate is approved unreviewed (reproduced: it lands at `design`).

## Scope

- Facade operation `run_automation_phase` / `redrive_automation_phase`
  (`modules/editorial/infrastructure/carousel_automation_run.py`): in-flight guard, revise
  revision-cap check, `lock_version` CAS, `mark_resume_in_progress`, **commit**, then the phase
  runs inline through the same run-owned wrapper the HTTP route schedules
  (`execute_resume_run`: epoch fence, heartbeat loop, run events, own session, failure marking).
- The driver's `resume` uses it; new `redrive`. Refusals map to `VERSION_CONFLICT`,
  `REVISION_CAP`, `IN_PROGRESS`, `NOT_PARKED`.
- Engine `continue_pending` (`ainvoke(None)`, never a null resume) + `is_parked`; service
  `redrive_pending_phase` / `is_parked_before_node`; runner wrapper accepts
  `RUN_ACTION_REDRIVE`.
- Parked guard: `read_gate` reconciles the checkpoint with the row (`domain/parked.py`). A run in
  flight → wait (or stale → escalate); row `failed` → escalate `phase_failed`; otherwise parked:
  wait 10 minutes, then `REDRIVE` (`approved` / `in_progress`) or `ESCALATE
  engine_parked_no_run_in_flight` (Telegram notice through the escalation path).
- Ops recovery script `backend/scripts/redrive_parked_carousel.py` (dry run by default).
- Tests with the real `EditorialWorkflowService`, graph, interrupts, run wrapper, file SQLite;
  Gherkin in `backend/tests/features/autopilot_runner.feature`.
- Doc: `docs/architecture/grokbot-autopilot.md`.

## Non-Goals

- Do not refactor unrelated code.
- No DB migration (prod deploys don't run Alembic): the grace period uses the existing
  `carousel_projects.updated_at`.
- Do not run anything against prod; the orchestrator runs the recovery.
- The HTTP resume path has the same null-resume trap when a user re-approves a parked
  checkpoint; noted as a follow-up, not changed here.

## Acceptance Criteria

- [x] After an autopilot approve of the outline, the content phase runs: drafts exist, the
  workflow waits at `content/awaiting_human`, the content gate is not approved, the row is at
  `content/awaiting_human` with `lock_version` bumped once, `run.finished(completed)`.
- [x] While the phase runs the row is `in_progress` with `run_started_at` set, the heartbeat loop
  refreshes `run_heartbeat_at`, and the tick holds no open transaction.
- [x] A provider error in the next phase marks the row `failed`, publishes
  `run.finished(failed)`, and the next tick escalates `phase_failed`.
- [x] Parked guard: wait inside the 10-minute grace; after it re-drive (`approved` /
  `in_progress`) or escalate `engine_parked_no_run_in_flight`; a re-drive with nothing parked
  writes nothing and escalates.
- [x] A re-drive re-runs the pending node with no review decision; the content gate still needs
  the policy check.
- [x] A run in flight is never resumed twice; a capped revise is refused before any write.
- [x] Other in-process calls checked: start, revise, rework apply, owner final-review approve.
- [x] Recovery script for 8e350d6e, tested against the parked shape (dry run + apply + refusal).
- [x] Python 3.11 import check: every `rag_backend` module imports.

## Repro Steps

1. Carousel at the outline gate; the content phase raises `openai.APITimeoutError`.
2. Before the fix: `driver.resume(approve)` returns `PROVIDER_OUTAGE`; checkpoint
   `content/approved` (next=`content`, no interrupt); row `outline/awaiting_human`,
   `run_started_at` NULL; `decide()` → WAIT `waiting`. Reproduced in a scratch test against
   the real service before the fix.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

AE-0362 (merged).

## Other in-process calls (requirement 6)

- start (`InProcessEditorialDriver.start` → `EditorialWorkflowHandlers.start`): mirrors the
  synchronous HTTP start route, commits through the handler, and an outage is counted toward
  `MAX_START_ATTEMPTS`. Research synthesis runs before the graph checkpoint exists, so it cannot
  park. Unchanged; the parked guard covers any odd state.
- revise (runner `_revise`): same path as approve → fixed.
- rework apply (`ReworkStep`): uses `driver.resume(revise, target_phase)` → fixed; refusals keep
  their meaning (`REVISION_CAP` escalates, others → `owner_rework_not_applied`).
- owner Telegram approve at final review (`owner_actions._approve_resume`): uses
  `driver.resume` → now the same run-owned path (no LLM at that gate).

## Progress Log

### 2026-10-14

Ticket created from the prod incident. Root cause verified against the code and reproduced with
the real service (scratch test). Test-first regression suite, then the fix. Full backend gate run
on c9f95588: PASS=21 FAIL=0 SKIP=0 (mutation 78.44%). Python 3.11 import check: 706 modules,
0 failures. Moved to Dev Complete.

## Files Touched

- `backend/src/rag_backend/modules/editorial/infrastructure/carousel_automation_run.py` (new)
- `backend/src/rag_backend/modules/editorial/infrastructure/carousel_automation.py`
- `backend/src/rag_backend/modules/editorial/public.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/editorial_driver.py`
- `backend/src/rag_backend/modules/autopilot/application/runner.py`
- `backend/src/rag_backend/modules/autopilot/domain/gate.py`
- `backend/src/rag_backend/modules/autopilot/domain/parked.py` (new)
- `backend/src/rag_backend/modules/autopilot/domain/policy.py`
- `backend/src/rag_backend/modules/autopilot/domain/snapshot.py`
- `backend/src/rag_backend/modules/autopilot/parked_constants.py` (new)
- `backend/src/rag_backend/agents/carousel_workflow_engine.py`
- `backend/src/rag_backend/agents/carousel_editorial_orchestrator.py`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_resume_runner.py`
- `backend/src/rag_backend/domain/constants/carousel_workflow.py`
- `backend/scripts/redrive_parked_carousel.py` (new)
- Tests: `tests/integration/test_autopilot_resume_runs_phase.py` (new),
  `tests/unit/modules/autopilot/test_parked_guard_ae0363.py` (new),
  `tests/unit/application/test_editorial_workflow_redrive_ae0363.py` (new),
  `tests/unit/agents/test_parked_before_node_ae0363.py` (new),
  `tests/unit/modules/autopilot/test_editorial_driver_outcomes.py`,
  `tests/unit/application/test_editorial_workflow_resume_runner.py`,
  `tests/features/autopilot_runner.feature`
- `docs/architecture/grokbot-autopilot.md`

## Test Evidence

See `.agent/reports/AE-0363.dev-summary.md` (GATES_JSON line).

## QA Report

Pending.

## Blockers

None.
