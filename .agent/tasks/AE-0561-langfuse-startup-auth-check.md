# AE-0561 — Verify Langfuse credentials without blocking startup

Status: Dev Complete
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

- After shared initialization returns a client, schedule one Langfuse public projects API request through the SDK on a tracked asyncio task and move its blocking call to a thread.
- Bound both the SDK request and asynchronous wait with a five-second timeout, disable request retries, and never await the check on the startup path or allow an auth exception to escape.
- Emit exactly one of `langfuse_auth_ok`, `langfuse_auth_failed`, or `langfuse_auth_unreachable` per scheduled check, with only a credential-free host and safe reason metadata.
- Preserve the existing client and callback handler on failure so tracing remains best-effort rather than being disabled.
- Add fake-client tests, Gherkin, and Langfuse setup/troubleshooting documentation.

## Non-Goals

- No network in tests, live credential verification, retries, new feature flags, or client shutdown redesign.
- No startup failure, synchronous auth call, key/header/exception-body logging, or behavior change to unrelated telemetry.
- No schema, API, frontend, deployment-workflow, or migration change.

## Acceptance Criteria

- [x] AC1 Configured web and worker startup shares one asynchronous credential-check path; scheduling does not wait for a blocked fake check, the check runs off the main thread, and both the request and await have a five-second deadline.
- [x] AC2 A successful check logs one `langfuse_auth_ok`; an empty projects response, 401, or API/SDK exception logs one warning `langfuse_auth_failed` with a status code or exception type; a timeout or transport exception logs one warning `langfuse_auth_unreachable` with its exception type.
- [x] AC3 Auth failures never raise or disable the existing tracing client or callback handler, and no planted public/secret key, authorization header, credential-bearing configured host or request URL, response body, traceback, or exception message appears in application logs.
- [x] AC4 Fake-client tests cover success, empty projects, 401, outer and SDK timeouts, transport and unexpected exceptions, asynchronous startup, exactly-once logging, request deadline/retry policy, tracing preservation, and secret redaction without network; the Langfuse guide documents the new log lines.
- [ ] AC5 Targeted tests, lint/type checks, full non-mutation backend gates, independent QA, and every PR CI workflow pass; mutation runs only in CI.

## Gherkin Scenarios

`backend/tests/features/langfuse_auth_check_ae0561.feature`:

- Valid Langfuse credentials log success without delaying startup
- Rejected Langfuse credentials log an authentication failure
- A timed out credential check logs unreachable
- A credential check exception is contained without secrets
- Diagnostic hosts contain only credential-free origins

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

The six focused tests failed before implementation because scheduling and timeout support were absent. The first implementation used a tracked asyncio task, thread offload, five-second deadline, status/type-only reasons, and shared startup wiring.

Review-driven hardening replaced the SDK `auth_check()` wrapper with its underlying public projects API request so the SDK cannot emit auxiliary raw-exception logs. The request and await both have a five-second deadline, retries are disabled, and diagnostic hosts are reduced to credential-free HTTP(S) origins. Seven revised behavioral tests failed before those changes; those seven plus three safe-host edge cases now pass alongside 40 existing Langfuse initialization/tracing tests. The async test holds the fake request blocked until after startup returns, and failure tests verify that both tracing clients and the callback handler remain available.

The final full backend capture used a fresh isolated PostgreSQL 17 database and passed 26 gates with zero failures; only CI-only mutation skipped. The suite reported 7,770 passed and 2 pre-existing skips, 95% total coverage, and 100% diff coverage. Integrity reported zero blockers and warnings. Independent QA and PR CI are pending.

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

- Failing first: six tests failed with missing `schedule_langfuse_auth_check` and `_LANGFUSE_AUTH_TIMEOUT_SECONDS`; all seven review-hardening tests also failed before the public-API and safe-host changes.
- Passing after implementation: ten tests cover async startup/success, empty projects, 401, transport, SDK and outer timeouts, unexpected exception, late completion, exactly-once events, no-retries/five-second request options, tracing preservation, off-main-thread execution, planted-secret containment, IPv6 origins, unsupported schemes, and malformed ports.
- Existing coverage: 40 Langfuse Cloud, callback, and trace I/O tests joined the ten new tests; all 50 passed.
- Focused Ruff format and lint checks pass.
- Full `gate-capture.sh backend`: 26 PASS, 0 FAIL, 1 CI-only mutation SKIP; 7,770 tests passed, 2 pre-existing skips, 95% total coverage, 100% diff coverage, migrations and schema drift PASS on a fresh isolated database. Integrity: 0 blockers, 0 warnings. Independent QA and PR CI are pending.

## QA Report

Pending.

## Decision Log

- 2026-10-27 (Pedro): check credentials off the startup path with a short timeout and never fail startup.
- 2026-10-27 (Pedro): tracing remains best-effort; the implementation will not disable the client on auth failure.
- 2026-10-27 (implementation): empty-projects/API/SDK failures are `failed`; timeout/transport failures are `unreachable`; only status codes and exception types are safe reasons.
- 2026-10-27 (implementation): use the SDK's public projects API directly instead of its logging `auth_check()` wrapper; log only a sanitized origin so credentials in configuration or exception payloads cannot reach the new diagnostics.

## Blockers

None.

## Final Summary

Pending.
