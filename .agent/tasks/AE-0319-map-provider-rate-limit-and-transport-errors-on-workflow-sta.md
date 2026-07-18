# AE-0319 — map provider rate-limit and transport errors on workflow start to structured 429/503 instead of generic 500

Status: Review
Tier: T1
Priority: Medium
Type: Bugfix
Area: backend
Owner: Unassigned
Branch: TBD
Created: 2026-07-17
Updated: 2026-07-17

## Goal

A provider outage/rate-limit during editorial workflow start surfaces as a
structured, retryable HTTP error (429/503 with a specific detail), not a
generic 500.

## Problem

Observed live 2026-07-17 22:26 UTC (post-AE-0318 deploy): the OpenCode Go GLM
endpoint returned 429 GoUsageLimitError ("5-hour usage limit reached") on the
first synthesis call of `POST /carousels/{id}/workflow/start`. AE-0318 mapped
`ValueError` (parse failures) to an observable 400, but provider exceptions
(`openai.RateLimitError`, `APIError`, timeouts) on the FIRST `ainvoke` in
`SourceSynthesisAgent.extract_key_points` (and in outline/content generation)
propagate unmapped -> `500 {"error": "Internal Server Error"}` with no
actionable detail for the client. Note: the repair-path transport guard
(AE-0318) covers only the repair call, by design.

## Scope

- Catch provider errors (`openai.RateLimitError` -> 429 with Retry-After when
  available; other `openai.APIError`/transport -> 503) at the workflow-start
  route boundary, with a `workflow_start_provider_error` structlog event.
- Constants for the new details; feature scenarios; route regression tests.

## Non-Goals

- Do not refactor unrelated code
- ...

## Acceptance Criteria

- [ ] openai/anthropic RateLimitError on workflow start returns 429 with detail provider_rate_limited.
- [ ] Other openai/anthropic APIError (incl. connection errors) returns 503 with detail provider_unavailable.
- [ ] Both paths log workflow_start_provider_error with project_id and detail.
- [ ] Non-provider exceptions propagate unchanged (no blanket catch).

## Repro Steps

1. Exhaust the OpenCode Go 5-hour window (or stub the LLM to raise
   `openai.RateLimitError`).
2. POST `/api/carousels/{id}/workflow/start` with any valid payload.
3. Observe `500 {"error": "Internal Server Error"}` and an `unexpected_error`
   log instead of a 429 with a retry hint.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

None.

## Progress Log

### 2026-07-17 HH:mm

Ticket created.

## Files Touched

See `.agent/reports/AE-0319.dev-summary.md`.

## Test Evidence

Full backend gates (post r1-fix rerun): see GATES_JSON in the dev summary.
Suites reproduced by hand: unit 2465 passed / 1 skipped, integration 413
passed / 6 skipped, safety-net 23 passed. mypy strict clean, ruff + format
clean. Per-AC test mapping in the dev summary.

## QA Report

External QA converged (mode: external, GLM 5.2 via OpenCode Go): r1 FAIL
(1 blocker / 3 major) -> fix round -> r2 verify-only PASS. Reports:
`.agent/reports/wave-ae0319-0321.qa.md` (+ per-ticket copy), rounds in
`.agent/reports/wave-ae0319-0321.external-review.r{1,2}.md`.

## Blockers

None.
