# AE-0561 — Verify Langfuse credentials without blocking startup

Status: In Development
Tier: T2
Priority: High
Type: Bug
Area: Backend
Owner: Kimi
Agent Lane: planner → architect → developer → qa → release
Branch: fix/ae-0561-langfuse-auth-check
Kanban Card: TBD
Created: 2026-10-27
Updated: 2026-10-27

## Goal

Emit one safe startup diagnosis for Langfuse credentials while keeping web and generation-worker startup immediate and tracing best-effort.

## Problem

`bootstrap/observability.py` logs `langfuse_initialized` whenever both keys exist, but never verifies them with Langfuse. A wrong key or region therefore appears healthy while every trace is rejected. The shared initializer is used by both the web application and generation worker.

## Scope

- After shared initialization returns a client, schedule one Langfuse SDK `auth_check()` on a tracked asyncio task and move its blocking call to a thread.
- Bound the asynchronous check with a five-second timeout; never await it on the startup path or allow an auth exception to escape.
- Emit exactly one of `langfuse_auth_ok`, `langfuse_auth_failed`, or `langfuse_auth_unreachable` per scheduled check, with only host and safe reason metadata.
- Preserve the existing client and callback handler on failure so tracing remains best-effort rather than being disabled.
- Add fake-client tests, Gherkin, and Langfuse setup/troubleshooting documentation.

## Non-Goals

- No network in tests, live credential verification, retries, new feature flags, or client shutdown redesign.
- No startup failure, synchronous auth call, key/header/exception-body logging, or behavior change to unrelated telemetry.
- No schema, API, frontend, deployment-workflow, or migration change.

## Acceptance Criteria

- [x] AC1 Configured web and worker startup shares one asynchronous credential-check path; scheduling does not wait for a blocked fake check, and the check has a five-second deadline.
- [x] AC2 A successful check logs one `langfuse_auth_ok`; a false result, 401, or API/SDK exception logs one warning `langfuse_auth_failed` with a status code or exception type; a timeout or transport exception logs one warning `langfuse_auth_unreachable` with its exception type.
- [x] AC3 Auth failures never raise or disable the existing tracing client, and no planted public/secret key, authorization header, credential-bearing request URL, response body, traceback, or exception message appears in application logs.
- [x] AC4 Fake-client tests cover success, false, 401, timeout, unexpected exception, asynchronous startup, exactly-once logging, and secret redaction without network; the Langfuse guide documents the new log lines.
- [ ] AC5 Targeted tests, lint/type checks, full non-mutation backend gates, independent QA, and every PR CI workflow pass; mutation runs only in CI.

## Gherkin Scenarios

`backend/tests/features/langfuse_auth_check_ae0561.feature`:

- Valid Langfuse credentials log success without delaying startup
- Rejected Langfuse credentials log an authentication failure
- A timed out credential check logs unreachable
- A credential check exception is contained without secrets

## Delta

### ADDED

- Tracked asynchronous Langfuse auth verification with deadline and safe outcome classification.
- Focused fake-client tests and Gherkin scenarios.
- Operational documentation for the three new log events.

### MODIFIED

- Shared observability bootstrap schedules the check after client initialization.

### REMOVED

- None; existing `langfuse_initialized`, `langfuse_disabled`, and best-effort tracing behavior remain.

## Affected Areas

- Backend: Langfuse client background verification and shared observability composition.
- Frontend: none.
- Database: none.
- API: none.
- Tests: new unit tests and feature file; no network.
- Docs: Langfuse Observability Guide, this ticket, and delivery reports.
- Prompts/LLM: none.
- Observability: three structured auth outcome events with safe metadata.
- Deployment: no workflow change; both existing startup paths inherit the behavior.

## Dependencies

- Blocks: actionable diagnosis of rejected Langfuse Cloud credentials.
- Blocked by: none.
- Related: AE-0545 Langfuse Cloud migration and the existing nonblocking flush design.

## Implementation Plan

1. Add the ticket and Gherkin scenarios, then failing fake-client tests for async startup and all outcomes.
2. Implement a tracked task, thread offload, five-second deadline, safe classification, and shared startup wiring.
3. Update the Langfuse guide, run focused and full verification, complete independent QA, and open the PR.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-27

Ticket created from current `origin/main` in the dedicated AE-0561 worktree. SDK inspection confirmed `auth_check()` is synchronous and can raise a 401 `UnauthorizedError`; both production callers already have a running event loop. Pedro's requested behavior keeps startup and tracing best-effort, so the client will remain enabled on auth failure.

The six focused tests failed before implementation because scheduling and timeout support were absent. The implementation now uses a tracked asyncio task, thread offload, five-second deadline, status/type-only reasons, and shared startup wiring. All six new tests and 40 existing Langfuse initialization/tracing tests pass. The guide documents the three new events.

## Files Touched

- `backend/src/rag_backend/bootstrap/observability.py`
- `backend/src/rag_backend/infrastructure/langfuse_client.py`
- `backend/tests/unit/bootstrap/test_langfuse_auth_check_ae0561.py`
- `backend/tests/features/langfuse_auth_check_ae0561.feature`
- `docs/guides/LANGFUSE_OBSERVABILITY_GUIDE.md`
- `.agent/tasks/AE-0561-langfuse-startup-auth-check.md`
- `.agent/reports/AE-0561.dev-summary.md`
- `.agent/reports/AE-0561.qa.md`

## Test Evidence

- Failing first: six tests failed with missing `schedule_langfuse_auth_check` and `_LANGFUSE_AUTH_TIMEOUT_SECONDS`.
- Passing after implementation: six tests cover async startup/success, false, 401, transport, unexpected exception, timeout, late completion, exactly-once events, and planted-secret containment.
- Existing coverage: 40 Langfuse Cloud, callback, and trace I/O tests joined the six new tests; all 46 passed.
- Focused Ruff format and lint checks pass. Full gates and independent QA are pending.

## QA Report

Pending.

## Decision Log

- 2026-10-27 (Pedro): check credentials off the startup path with a short timeout and never fail startup.
- 2026-10-27 (Pedro): tracing remains best-effort; the implementation will not disable the client on auth failure.
- 2026-10-27 (implementation): false/API/SDK failures are `failed`; timeout/transport failures are `unreachable`; only status codes and exception types are safe reasons.

## Blockers

None.

## Final Summary

Pending.
