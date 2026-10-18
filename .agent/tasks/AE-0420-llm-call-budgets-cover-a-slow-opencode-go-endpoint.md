# AE-0420 — LLM call budgets cover a slow OpenCode Go endpoint

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Claude (orchestrator)
Branch: fix/ae-0420-llm-timeouts
Created: 2026-10-18
Updated: 2026-10-18

## Goal

Content drafting no longer times out, opens every breaker, and fails the phase when the OpenCode Go
endpoint is slow but answering.

## Problem

2026-10-18, autopilot runs 5b5701a6 / 790e8969 (projects 519c7b57 / 901e51bb, pov_news with Grok
covers): outline→content failed twice (07:11–08:46Z, then 12:29–12:31Z) with
`AllModelsUnavailableError`. Every breaker opened as "transient" with an empty message, which is an
`asyncio` timeout. The models were answering: a measured ~4,000-character draft took 13–134 s
(deepseek-v4.1-flash 13–83 s, qwen3.8-flash 134 s). The fast-role budget was 120 s per attempt.

## Scope

- `LLM_TIMEOUT_FAST_SECONDS` 120 → 300, `LLM_TIMEOUT_REASONING_SECONDS` 240 → 360,
  `LLM_TIMEOUT_FALLBACK_SECONDS` 180 → 300 (`llm_routing_constants.py`); the routed models and the
  model queue read them through `role_timeout`.
- Routing tests assert the constants instead of literals.

## Non-Goals

- Making the budgets env-configurable (follow-up if needed).
- Changing breaker thresholds.

## Acceptance Criteria

- [x] The fast role allows ≥ 300 s per attempt; reasoning ≥ 360 s and above fast; fallback ≥ fast.
- [x] Existing routing/queue tests pass against the constants.

## Gherkin

`backend/tests/features/llm_timeouts_ae0420.feature`.

## Repro Steps

1. On prod, ask `go:qwen3.8-flash` for a ~600-word draft: 134 s.
2. With a 120 s budget the call times out; three in a row open the breaker; content fails.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-18 12:45

Ticket created; constants raised; feature + unit tests.

## Files Touched

- backend/src/rag_backend/infrastructure/config/llm_routing_constants.py
- backend/tests/features/llm_timeouts_ae0420.feature
- backend/tests/unit/infrastructure/test_llm_timeouts_ae0420.py
- backend/tests/unit/infrastructure/test_llm_model_routing_ae0391.py

## Test Evidence

Pending (hotfix fast path gates).

## QA Report

Pending.

## Blockers

None.
