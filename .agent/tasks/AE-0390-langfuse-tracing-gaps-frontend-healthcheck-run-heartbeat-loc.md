# AE-0390 — Langfuse tracing gaps, frontend healthcheck, run-heartbeat lock waits

Status: In Development
Tier: T1
Priority: P0
Type: Bugfix
Area: backend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0390-tracing-healthcheck-heartbeat
Created: 2026-10-15
Updated: 2026-10-15

## Goal

Every editorial phase LLM call lands in a named, tagged Langfuse trace with full metadata; the
prod frontend container reports healthy; the run heartbeat never waits on the run's own row lock.

## Problem

Prod 2026-10-15, autopilot carousel `f21b2bdb-2cdc-460e-8542-6b7c92682f4c`:

1. **Tracing.** 10 GLM generations in 3 traces. Only `workflow_research` carried metadata;
   outline/content generations had none, one trace had no name, no trace had tags. Root cause:
   the old `propagate_attributes` put the metadata on a *span* (not the trace) and the resume
   path (HTTP runner + autopilot) opened no phase span, so every LangChain callback generation
   started its own anonymous trace. The autopilot wrapper also labelled the run with the *gate*
   phase (`research` while generating the outline).
2. **Healthcheck.** `frontend` `unhealthy` (1,201 failures). The Dockerfile probe
   `wget http://localhost:3000/api/health`: busybox resolves `localhost` to `[::1]`, Next.js
   listens on IPv4 only (and `/api/*` is proxied to the backend anyway).
3. **Heartbeat.** `carousel_run_heartbeat_failed` / `LockNotAvailableError` twice per phase.
   Holder: the run's own `db` session. `resume_workflow` flushes the phase sync
   (`CarouselProjectWriteOwner.sync_phase` → `UPDATE carousel_projects`) and the runner committed
   only at the very end, so finalize/export, review events, SSE and both stage beats
   (`VALIDATING`, `PERSISTING`, 2 s `lock_timeout` each) ran under that row lock: exactly two
   warnings per run. (No lock is held across the LLM call itself; the tick session commits
   before the run, the HTTP route commits before scheduling, `phase_progress` writes commit.)

## Scope

- `infrastructure/langfuse_phase_trace.py`: `phase_trace` (span + `update_trace` + Langfuse
  `propagate_attributes` with trace name, user, metadata, tags) and `workflow_trace_scope`
  (contextvar actor scope). Constants in `domain/constants/langfuse_tracing.py`.
- Seams: graph `ensure_artifacts` (outline/content incl. persona scoring + distribution,
  design, images), `start_workflow` research, autopilot `owner_autofix`. Legacy
  `propagate_attributes` delegates to `phase_trace` (blog paths gain tags too).
- Scope: `execute_resume_run` (HTTP + autopilot) sets project + owner (`read_project_owner_id`);
  the autopilot driver sets `agent_name=autopilot`.
- Healthcheck: frontend `ENV HOSTNAME=0.0.0.0` + probe `http://127.0.0.1:3000/robots.txt`;
  backend probe `127.0.0.1`. New gate `backend:healthcheck-loopback`
  (`scripts/ci/check_healthcheck_loopback.py`) + seeded-violation tests.
- Heartbeat: `resume_workflow` / `redrive_pending_phase` commit the phase sync at once
  (`_sync_and_release_row`), before finalize, review events, SSE and stage beats. This also
  removes a latent self-deadlock in the stuck-revert path (its separate-session UPDATE waited on
  the same uncommitted row with no timeout).

## Non-Goals

- No DB migration. No change to heartbeat SQL (`SKIP LOCKED` / jitter not needed once the
  holder is fixed: no remaining overlap holds the row).
- No change to the compose files (they define no frontend/backend healthcheck; the Dockerfile
  `HEALTHCHECK` is the one prod runs).

## Acceptance Criteria

- [x] Each phase resume (outline, content via the HTTP runner; design, images via the graph
  seam) emits `workflow_<phase>` with the 5 metadata keys and the 3 tags.
- [x] The autopilot path (driver → `run_automation_phase` → run wrapper) does the same with
  `agent_name=autopilot`, `user_id=<owner>`; autopilot start traces research likewise.
- [x] Frontend healthcheck probes `127.0.0.1`; CI gate fails on any `localhost` healthcheck
  (seeded-violation tests, AE-0180).
- [x] Heartbeat root cause fixed; Postgres two-session test: heartbeat succeeds during the
  phase LLM call, a second session updates the row after the sync within the run lock timeout,
  and no `carousel_run_heartbeat_failed` is logged (relayed: needs Postgres).
- [ ] Python 3.11 import check (relayed).

## Gherkin Scenarios

`backend/tests/features/workflow_tracing_and_heartbeat.feature`

## Affected Areas

- [x] Backend
- [x] Frontend (Dockerfile only)
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-15

Ticket created (hotfix fast path). `create_ticket.py` proposed AE-0379; renamed to AE-0390 as
the brief requires. Implemented the three fixes, Gherkin + tests. See
`.agent/reports/AE-0390.dev-summary.md`.

## Files Touched

- `frontend/Dockerfile`, `backend/Dockerfile`, `scripts/ci/check_healthcheck_loopback.py`,
  `scripts/ci/gates.sh`
- `backend/src/rag_backend/infrastructure/langfuse_phase_trace.py` (new),
  `infrastructure/monitoring_langfuse.py`, `domain/constants/langfuse_tracing.py` (new)
- `backend/src/rag_backend/agents/carousel_workflow_nodes.py`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py`,
  `editorial_workflow_resume_runner.py`
- `backend/src/rag_backend/modules/editorial/infrastructure/carousel_run_progress.py`, `public.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/editorial_driver.py`,
  `content_autofixer.py`, `modules/autopilot/constants.py`
- Tests: `tests/langfuse_trace_fakes.py`, `tests/unit/infrastructure/test_langfuse_phase_trace_ae0390.py`,
  `tests/unit/agents/test_phase_trace_nodes_ae0390.py`, `tests/unit/application/test_phase_sync_release_ae0390.py`,
  `tests/integration/test_phase_traces_ae0390.py`, `tests/integration/test_run_heartbeat_lock_pg.py`,
  `tests/unit/scripts_ci/test_check_healthcheck_loopback.py`; updated
  `tests/integration/test_autopilot_runner_start.py`, `tests/unit/application/test_editorial_workflow_resume_runner.py`
- Docs: `docs/guides/LANGFUSE_OBSERVABILITY_GUIDE.md`

## Test Evidence

See `.agent/reports/AE-0390.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
