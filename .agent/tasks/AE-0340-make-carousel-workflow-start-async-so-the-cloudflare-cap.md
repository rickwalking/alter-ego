# AE-0340 — make carousel workflow/start async so the Cloudflare 100s cap cannot kill a run

Status: Ready
Tier: T2
Priority: High
Type: Feature
Area: Backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-09-15
Updated: 2026-09-15

## Goal

Start a carousel run by **accepting the job**, not by holding an HTTP connection
open for the length of the first phase. No proxy or CDN timeout should be able to
lose the result of work the backend actually completed.

## Problem

`POST .../workflow/start` runs the first phase synchronously and only then
responds. On 2026-09-14 that took ~68 s while nginx's `location /api/` had no
`proxy_read_timeout` (60 s default) — the backend **finished the work and the
response was thrown away**, surfacing to the user as a 504.

AE-0330 raised nginx to 300 s, which removed the immediate symptom. It did not
remove the class:

- **Cloudflare still caps the request at roughly 100 s**, and that limit is not
  ours to raise. A first phase slower than ~100 s fails the same way — backend
  work done, response lost, user sees an error.
- A long-held request is fragile to any client, mobile network, or intermediate
  proxy dropping the connection.
- Retrying looks free to the user but re-runs real LLM work (the UI's "retry" is
  `workflow/start`, a full restart).

The durable fix is an async start: accept, enqueue, return an identifier, and let
the client poll or stream progress — which the system already does for later
phases.

## Scope

- `POST .../workflow/start` returns promptly (202-style) with the project/run
  identifier after persisting the intent; the first phase executes in the
  background worker path used by the rest of the workflow.
- Idempotency: a repeated start for the same project must not launch a second run
  (workflow state changes are idempotent — root `CLAUDE.md`). Guard on the
  existing lock/version mechanism.
- Progress surfaced through the existing status/streaming channel so the UI can
  show "starting" without holding a request.
- Frontend: stop waiting on the synchronous response; move to the poll/stream path
  already used for subsequent phases.
- Failures in the background start must land in the project's status with a
  reason, not vanish.

## Non-Goals

- Rewriting the phase execution engine.
- Removing the nginx 300 s timeout (harmless once the start is async; leave it).
- Changing Cloudflare configuration.

## Acceptance Criteria

- [ ] `workflow/start` responds in well under 10 s regardless of first-phase duration.
- [ ] The first phase completes in the background and its result is visible via
      the existing status endpoint.
- [ ] A second `start` for the same project while one is in flight does not
      launch a duplicate run and returns a clear response.
- [ ] A background start failure is recorded as a failed phase with a reason and
      is visible in the UI.
- [ ] The frontend no longer depends on the long-held response.
- [ ] A test simulates a client disconnect mid-start and asserts the run still
      completes.

## Gherkin Scenarios

```gherkin
Feature: Asynchronous carousel start

  Scenario: Start returns immediately
    Given a new carousel project
    When the client posts to workflow/start
    Then the response arrives within a few seconds
    And it carries the identifier the client can poll

  Scenario: The client disconnects during the first phase
    Given a start request has been accepted
    When the client disconnects
    Then the first phase still completes
    And its result is readable from the status endpoint

  Scenario: Double start is idempotent
    Given a run is already in flight for the project
    When another start is posted
    Then no second run is launched
    And the response names the run already in flight

  Scenario: A background failure is visible
    Given the first phase fails in the background
    When the client reads the status
    Then it shows the phase as failed with a reason
```

## Affected Areas

- Backend: carousel workflow start route, background execution path, idempotency guard
- Frontend: create-carousel flow — poll/stream instead of awaiting
- Database: run/lock state
- API: `workflow/start` response contract changes — regenerate the pinned
  artifacts (openapi.json, route snapshot, publishing + editorial workflow snapshots)
- Tests: engine + API + frontend
- Docs: carousel workflow guide
- Prompts/LLM: no
- Observability: trace the background start with the standard metadata
- Deployment: no

## Dependencies

- Blocks: reliable carousel creation over Cloudflare
- Blocked by: none
- Related: AE-0330 (nginx timeout), AE-0339 (status reporting)

## Implementation Plan

1. Architect pass: choose the background execution path (existing worker vs task)
   and the response contract; note it in the ticket's Decision Log.
2. Implement accept-and-enqueue with the idempotency guard.
3. Move the frontend to poll/stream.
4. Add the disconnect and double-start tests.
5. Regenerate the four pinned backend artifacts for the contract change.

## QA Checklist

- [ ] Security reviewed (auth on the accepted job)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (disconnect, double start, backend restart mid-phase)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Ticket created from the AE-0330 session handoff. AE-0330 raised the nginx
timeout to 300 s; the Cloudflare ~100 s cap keeps the class alive.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
