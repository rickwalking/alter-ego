# AE-0208 — Provider-rate-limit-aware image generation (concurrency cap + retry-after)

Status: Intake
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
