# AE-0574 — Owner-approved Instagram boost requests

Status: Ready
Tier: T2
Priority: P1
Type: Feature
Area: backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: feat/ae-0574-boost-requests
Kanban Card: TBD
Parent: AE-0572
Created: 2026-10-29
Updated: 2026-10-29

## Goal

The autopilot API key can create and read boost requests. Each new request sends the owner one Telegram message with Approve and Reject. Nothing in this ticket calls the Marketing API. `BOOST_ENABLED` stays false.

## Problem

Phase 1 can rank posts, but there is no stored request, no cap, and no owner decision. A later worker must not invent an approval.

## Scope

Implement phase 2 of `.agent/reports/AE-0572.arch-plan.md`:

- `POST /api/autopilot/boost-request`, `GET /api/autopilot/boost-request/{id}`, `GET /api/autopilot/boost-requests`.
- Idempotency-Key, policy caps, one open request per media id.
- Tables `boost_requests` and `boost_request_events` (revision `a8b9c0d1e2f3` on `f9a0b1c2d3e4`).
- Telegram plain-text prompt and callbacks `ap:bst:ok:` / `ap:bst:no:`.
- Tick that expires pending requests and retries a missing Telegram message. No ads client.
- Env parity for every new `BOOST_*` setting, both switches default false.
- Fill `boost` on the phase 1 insights response.

## Non-Goals

- Creating, activating, pausing or reading live ads (AE-0575).
- `ap:bst:stop`.
- Awareness objective, interests, custom audiences.
- HTML parse mode.
- Expiring an approved request because the worker has not launched it.

## Acceptance Criteria

- [ ] WHEN a request exceeds any cap THE API SHALL return 422 with the stable `detail` code AND store nothing.
- [ ] WHEN a second non-terminal request targets the same media THE API SHALL return 409 `boost_already_active`.
- [ ] WHEN the same Idempotency-Key and body are replayed THE API SHALL return the original row with 200; a different body SHALL return 409 `idempotency_key_reused`. A new key SHALL return 202 `pending_approval`.
- [ ] WHEN a request is created THE owner chat SHALL receive one plain-text message with Approve and Reject buttons.
- [ ] WHEN a chat other than `TELEGRAM_OWNER_CHAT_ID` taps a button THE row SHALL NOT change.
- [ ] WHEN 12 hours pass without a decision THE row SHALL become `expired` AND the Telegram message SHALL say so.
- [ ] WHEN the owner approves after the weekly cap has been lowered THE row SHALL become `failed` with the policy code AND SHALL NOT become `approved`.
- [ ] WHEN `BOOST_ENABLED` is false AND a request is `approved` THE worker SHALL make zero Marketing API calls AND SHALL leave the row `approved`.
- [ ] WHEN `BOOST_REQUESTS_ENABLED` is false THE create route SHALL return 503 `boost_disabled`.
- [ ] Env parity and the single Alembic head `a8b9c0d1e2f3` pass. OpenAPI snapshot includes the three routes.

## Gherkin Scenarios

```gherkin
Feature: Owner-approved Instagram boost requests

  Scenario: Bot requests a boost and the owner approves
    Given the daily budget cap is 3000 cents
    And media "18034567890123456" is a 47-hour-old feed carousel in ig_media
    When the bot posts a boost request of 2000 cents for 3 days with key "k1"
    Then the response is 202 with status pending_approval
    And the owner chat receives Approve and Reject buttons
    When the owner taps Approve
    Then the request status is approved

  Scenario: A stranger cannot approve
    Given a pending boost request
    When a non-owner chat taps Approve
    Then the request status is still pending_approval

  Scenario: Over the weekly cap
    Given 9000 cents are committed this week and the cap is 10000
    When the bot requests 2000 cents for 1 day
    Then the response is 422 weekly_cap_exceeded
    And no row is stored

  Scenario: Idempotency replay
    Given a request stored under key "k1"
    When the bot repeats the same key and body
    Then the response is 200 with the original id
    When the bot repeats the same key with a different budget
    Then the response is 409 idempotency_key_reused

  Scenario: Pending request expires
    Given a pending request whose expires_at is in the past
    When the worker ticks
    Then the status is expired
```

## Delta

### ADDED

- Three boost routes, two tables, boost domain/application/infrastructure modules, boost tick (expire and Telegram retry only).
- `RATE_LIMIT_AUTOPILOT_BOOST`.
- Settings listed in the architecture plan except the ads-token settings (those are AE-0575). This ticket adds `BOOST_REQUESTS_ENABLED`, `BOOST_ENABLED` (default false, unused for calls), the cap settings, `BOOST_ALLOWED_COUNTRIES`, `BOOST_APPROVAL_TTL_HOURS`, `BOOST_CURRENCY`.
- `backend/tests/features/autopilot_boost_approval.feature`.

### MODIFIED

- `owner_actions._on_callback` chain.
- `bootstrap_webhook.py`, worker factory, settings, env parity script and its rule-fires test.
- Phase 1 insights item `boost` field.
- OpenAPI snapshot and `ALEMBIC_HEAD`.

### REMOVED

- None.

## Affected Areas

- Backend: `modules/autopilot`, settings, worker bootstrap
- Frontend: none
- Database: one additive migration
- API: three routes
- Tests: unit, API, webhook, Gherkin, migration, env parity
- Docs: `docs/architecture/grokbot-autopilot.md`
- Prompts/LLM: none
- Observability: boost request events
- Deployment: new env names, switches default false

## Dependencies

- Blocks: AE-0575
- Blocked by: AE-0573
- Related: AE-0356, AE-0359, ADR-0020, ADR-0029

## Implementation Plan

1. Feature file, then policy and state tests.
2. Migration and store, then routes and idempotency.
3. Mixin on `OwnerActionService` without expanding `handle` past the existing arguments.
4. Tick for expiry and one-time Telegram retry. Do not construct an ads client.
5. Env parity, contract regen, `ALEMBIC_HEAD=a8b9c0d1e2f3`.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-29 18:20

Ticket opened from the architecture plan.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- Committed weekly spend includes pending, failed, stopped and completed rows in the rolling 7 days, summed as `total_budget_cents`.
- Approve that fails a later policy check becomes `failed`, not `rejected` and not left pending.
- Telegram copy is Portuguese plain text. `reason` goes through `strip_controls`.
- `BOOST_ENABLED` is present and default false so phase 3 does not need a second parity change for the switch, but this ticket must not call Graph ads.

## Blockers

None.

## Final Summary

Pending.
