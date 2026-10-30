# AE-0572 — Instagram boost bot

Status: Ready
Tier: T3
Priority: P1
Type: Epic
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0572-ig-boost
Kanban Card: TBD
Parent: AE-0348
Created: 2026-10-29
Updated: 2026-10-29

## Goal

Let a boost bot read organic Instagram performance with the autopilot API key, request a boost, and spend money only after the Telegram owner approves. The bot never holds a Meta token.

## Problem

`GET /api/instagram/insights` is editor/admin JWT only, lists only posts this backend published, and omits likes, comments, media type and timestamps. Nothing in the backend can create an ad. The live token is an Instagram Login token and cannot call the Marketing API.

## Scope

- Phase 1 (AE-0573): `GET /api/autopilot/ig-insights`.
- Phase 2 (AE-0574): boost-request routes, `boost_requests`, Telegram Approve/Reject. Spending switch stays off.
- Phase 3 (AE-0575): worker launches approved boosts on a separate ads token. `BOOST_ENABLED` defaults off.
- ADR-0029 and the architecture plan `.agent/reports/AE-0572.arch-plan.md`.

## Non-Goals

- The bot calling the Marketing API, or any `X-Api-Key` route calling it.
- Custom audiences, lookalikes, new creatives, or a dashboard UI.
- Changing `GET /api/instagram/insights` or the Instagram Login publish flow.
- Editing a live ad from Telegram except Stop in phase 3.
- Awareness objectives in v1.

## Acceptance Criteria

- [ ] WHEN phase 1 is deployed THE bot CAN rank account media, including posts this backend did not publish, from `GET /api/autopilot/ig-insights` alone.
- [ ] WHEN phase 2 is deployed with `BOOST_ENABLED=false` THE owner CAN approve or reject in Telegram AND the worker SHALL make zero Marketing API calls.
- [ ] WHEN phase 3 launches an approved request THE ads SHALL be created paused, ids stored after each step, and activated only while `BOOST_ENABLED` is true.
- [ ] WHEN ADR-0029 is still proposed THE phase 3 kill switch SHALL stay off in production.

## Gherkin Scenarios

```gherkin
Feature: Instagram boost epic

  Scenario: Phases ship without spending
    Given phase 1 and phase 2 are deployed
    And BOOST_ENABLED is false
    When the bot reads insights and creates a boost request
    And the owner approves it
    Then the request status is approved
    And no Marketing API request has been made
```

## Delta

### ADDED

- Child tickets AE-0573, AE-0574, AE-0575.
- ADR `docs/decisions/0029-owner-approved-instagram-boosts.md` (proposed).
- Architecture plan `.agent/reports/AE-0572.arch-plan.md`.

### MODIFIED

- None in this epic ticket. Children carry the code delta.

### REMOVED

- None.

## Affected Areas

- Backend: `modules/autopilot`, bootstrap, settings
- Frontend: none
- Database: two additive migrations (children)
- API: four routes (children)
- Tests: children
- Docs: ADR-0029, `docs/architecture/grokbot-autopilot.md`
- Prompts/LLM: none
- Observability: `boost.*` logs and `boost_request_events`
- Deployment: new secrets, both switches default off

## Dependencies

- Blocks: the external boost bot's live spending
- Blocked by: none for phase 1. Phase 3 is blocked by the Meta checklist in the architecture plan and by accepting ADR-0029.
- Related: AE-0348, AE-0349, AE-0371, AE-0378, ADR-0020, ADR-0021

## Implementation Plan

1. Develop AE-0573, then AE-0574, then AE-0575.
2. Follow `.agent/reports/AE-0572.arch-plan.md`. Where this ticket and that plan disagree, the plan wins.
3. Do not set `BOOST_ENABLED=true` until ADR-0029 is accepted and one test-account boost has been checked in Ads Manager.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-29 18:20

Epic opened from the architecture plan. No production code yet.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- Tier is T3, not T1. Phase 1 and phase 2 ship before any ads token exists.
- Separate System User token for ads. The Instagram Login token stays on `graph.instagram.com`.
- API key can only create `pending_approval` and read. Approval is a Telegram owner callback.
- Ads objects are created paused and activated last.
- Caps are enforced at create, approval and launch. Weekly window is a rolling 7 days by `created_at` UTC.
- Version 1 accepts `engagement` only.
- Approved rows do not expire while waiting. Only `pending_approval` expires (12 h).
- `BOOST_MIN_DAILY_BUDGET_CENTS` default 600 is the product floor, not Meta's published BRL minimum. Launch also checks the ad account minimum-budget endpoint.
- Alembic revisions are `f9a0b1c2d3e4` then `a8b9c0d1e2f3`, chained from head `e7a91c4d2f60`. Do not reuse `a1b2c3d4e5f6` or `b2c3d4e5f6a7`.

## Blockers

Phase 3: Meta checklist and ADR-0029 acceptance.

## Final Summary

Pending.
