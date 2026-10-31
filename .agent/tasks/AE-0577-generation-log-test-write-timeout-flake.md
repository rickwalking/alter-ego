# AE-0577 — Generation-log integration test flakes on the 100 ms event write timeout

Status: Intake
Tier: T1
Priority: Medium
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa
Branch: TBD
Kanban Card: TBD
Created: 2026-10-30
Updated: 2026-10-30

## Goal

`tests/integration/test_carousel_generation_log_ae0556.py::test_stored_rows_and_api_exclude_sensitive_failure_content`
passes deterministically on a loaded machine, without weakening what it proves or the production write budget.

## Problem

The generation-event recorder gives each write `EVENT_WRITE_TIMEOUT_SECONDS = 0.1`
(`modules/generation_queue/domain/generation_events.py:16`) so it never slows a generation; on timeout it logs
`generation_event_store_failed` and returns `False`. The test asserts `await record_generation_event(event) is True`
against real Postgres, so when the host is busy the 100 ms budget expires and the test fails with
`assert False is True` (log: `error_type: TimeoutError`). Seen on 2026-10-30 in two of four local full
`gate-capture.sh backend` runs (AE-0500 rebase, AE-0576); the test passes when run alone.

## Scope

- In the test (or its fixture), inject a test-only write timeout (e.g. patch the constant or make the recorder take the
  timeout from an injectable config) large enough for a loaded CI/laptop; keep the production 100 ms default.
- Keep a separate unit test proving the production timeout path still returns `False` and logs, without a DB.

## Non-Goals

- Changing the production write budget or the best-effort semantics.

## Acceptance Criteria

- [ ] AC1 Given a loaded host, When the generation-log integration tests run, Then the sensitive-content test does not
  depend on a 100 ms Postgres round trip.
- [ ] AC2 Given the production default, When a write exceeds it, Then the recorder still returns `False` and logs
  `generation_event_store_failed` (unit-tested).

## Dependencies

- Related: AE-0556 (generation log).
