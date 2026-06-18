# AE-0208 — Provider-rate-limit-aware image generation (concurrency cap + retry-after)

Status: Done
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

Image generation survives provider rate limits without failing the images phase.

Source: Kaizen prod sweep `.agent/reports/kaizen-prod-2026-06-18.plan.md` (live carousel run, project b5b61790-9372-4a5a-ae17-30d2df28ef3d), validated by an independent architect cold-critic review.

## Problem

`application/services/carousel/nodes/images.py:521` fires all slide images via `asyncio.gather` (uncapped fan-out). The OpenAI org image cap is 5/min; a 7-slide carousel 429s (prod: `Rate limit reached for gpt-image ... Limit 5, Used 5 ... try again in 12s`). **Correction (cold-critic):** `infrastructure/external/openai_image.py` has NO app-level retry — the only retries are the OpenAI SDK's internal `max_retries` (the ~0.38s/0.86s waits), which are far below the 12s `retry-after`.

## Scope

- Cap image-generation concurrency to a configurable provider limit (≤ the documented per-minute cap).
- On HTTP 429, honor the `retry-after` (exponential backoff ≥ the stated wait), via app-level retry or a raised/aware SDK `max_retries`.
- Seeded test: a stubbed 429 → the runner waits and succeeds instead of failing the phase.

## Non-Goals

- Raising the OpenAI account tier (ops action, out of code scope).

## Acceptance Criteria

- [ ] Concurrency capped to a config value; no uncapped `gather` fan-out for image calls.
- [ ] 429 `retry-after` honored (backoff ≥ stated wait).
- [ ] Seeded-429 test passes (the phase completes, does not abort).

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
- Related (extends): AE-0017 (carousel generation recovery epic)

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

### 2026-06-18 — Developer (worktree feat/kz-images)

Implemented concurrency cap + retry-after. New `image_rate_limit.py`
(`build_image_semaphore`, `generate_with_retry_after`) and
`image_generation_constants.py`; new settings `carousel_image_concurrency=5`,
`carousel_image_max_attempts=5`. Wired the semaphore + retry into
`_run_one_image`. Seeded tests added. ruff/mypy clean. See
`.agent/reports/AE-0208.dev-summary.md`.

## Files Touched

- backend/src/rag_backend/infrastructure/config/settings.py
- backend/src/rag_backend/application/services/carousel/image_rate_limit.py (new)
- backend/src/rag_backend/application/services/carousel/image_generation_constants.py (new)
- backend/src/rag_backend/application/services/carousel/nodes/images.py
- backend/tests/unit/application/test_phase5_parallel.py

## Test Evidence

`uv run pytest tests/unit/application/test_phase5_parallel.py` — 11 passed.
Seeded: `test_429_then_success_completes_phase`, `test_concurrency_capped_to_config`.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Shipped in PR #46. Image-gen concurrency capped (`carousel_image_concurrency`) via semaphore + 429 `retry-after` honored. Seeded tests: 429-then-success completes the phase; concurrency ≤ cap. Verified full backend gates incl. mutation 78.92%.
