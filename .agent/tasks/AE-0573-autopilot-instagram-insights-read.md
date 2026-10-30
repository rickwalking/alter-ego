# AE-0573 — Autopilot Instagram insights read

Status: In Development
Tier: T2
Priority: P1
Type: Feature
Area: backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: feat/ae-0573-ig-insights
Kanban Card: TBD
Parent: AE-0572
Created: 2026-10-29
Updated: 2026-10-29

## Goal

`GET /api/autopilot/ig-insights` returns organic performance for account media, including posts this backend did not publish, with type-specific metrics, rates and per-type medians. The autopilot API key is the only auth. The dashboard route stays unchanged.

## Problem

The boost bot cannot call `GET /api/instagram/insights`. That route is JWT editor/admin, limited to the 30 newest posts in `autopilot_runs` and the manual publish ledger, and it does not return likes, comments, media type, product type or timestamps.

## Scope

Implement phase 1 of `.agent/reports/AE-0572.arch-plan.md`:

- API-key route, shared autopilot rate limit, `Cache-Control: no-store`.
- Graph media list on `graph.instagram.com` (pinned v23.0), stories skipped, 4-page cap.
- Type-specific insights metrics. Deprecated metrics are never requested. Missing values stay null.
- Tables `ig_media` and four nullable columns on `instagram_post_insights`.
- Writers update only metrics they requested, so a dashboard refresh does not null the new columns.
- Rates, baselines, exclusive `until` paging, `list_truncated`.
- `scripts/ops/ig_scope_probe.py`.
- OpenAPI snapshot, `make regen-contracts`, route note in `docs/architecture/grokbot-autopilot.md`.

## Non-Goals

- Boost requests, Telegram, or the Marketing API (AE-0574, AE-0575).
- Changing the JWT insights response or the dashboard metric tuple `INSIGHT_METRICS`.
- Storing full captions or `media_url`.
- Account demographics.

## Acceptance Criteria

- [ ] WHEN the bot calls `GET /api/autopilot/ig-insights` with a valid key THE response SHALL list account media, including posts with no `carousel_project_id`, with type-appropriate metrics, rates and `FEED`/`REELS` baselines.
- [ ] WHEN a metric is unavailable or refused THE value SHALL be null, never 0, AND deprecated metric names SHALL NOT be sent to Graph.
- [ ] WHEN the key is missing or wrong THE route SHALL return 401; WHEN `GROKBOT_API_KEY_SHA256` is unset THE route SHALL return 503.
- [ ] WHEN `since` is more than 90 days ago OR `limit` is outside 1–100 THE route SHALL return 422.
- [ ] WHEN the dashboard insights path saves a snapshot THE new columns SHALL be left unchanged.
- [ ] WHEN the media walk hits the page cap THE response SHALL set `list_truncated` true.
- [ ] Alembic head is the single new revision `f9a0b1c2d3e4` on top of `e7a91c4d2f60`. Route snapshot and contract regen pass.

## Gherkin Scenarios

```gherkin
Feature: Autopilot Instagram insights

  Scenario: Account media with rates and baselines
    Given the account has a feed carousel and a reel
    And the carousel was not published by the backend
    When the bot gets ig-insights with a valid key
    Then both posts are listed
    And the carousel has follows and a null watch time
    And the reel has watch time and null follows
    And baseline has FEED and REELS

  Scenario: Refused metric stays null
    Given Graph omits likes for a post
    When insights are refreshed
    Then likes is null

  Scenario: Missing API key
    When ig-insights is called without a key
    Then the response is 401

  Scenario: Dashboard refresh does not clear likes
    Given a snapshot already has likes
    When the dashboard insights path refreshes views and reach only
    Then likes is unchanged
```

## Delta

### ADDED

- `GET /api/autopilot/ig-insights`.
- `ig_media` and insight columns (`f9a0b1c2d3e4`).
- Modules listed under Phase 1 in the architecture plan.
- `scripts/ops/ig_scope_probe.py`.
- `backend/tests/features/autopilot_ig_insights.feature`.

### MODIFIED

- `insights_gateway.media_insights` accepts a metrics tuple defaulting to the current dashboard set.
- `InsightSnapshot.written` and `insights_store._write`.
- `app_factory.py`, OpenAPI artifacts, `docs/architecture/grokbot-autopilot.md`, `ALEMBIC_HEAD`.

### REMOVED

- None.

## Affected Areas

- Backend: `modules/autopilot`
- Frontend: none
- Database: one additive migration
- API: one route
- Tests: unit, API, Gherkin, migration, route snapshot
- Docs: grokbot autopilot architecture
- Prompts/LLM: none
- Observability: existing `instagram.insights` log
- Deployment: none beyond the migration

## Dependencies

- Blocks: AE-0574
- Blocked by: none. Confirm `instagram_business_manage_insights` with the probe before trusting production numbers.
- Related: AE-0378, ADR-0020, ADR-0021, ADR-0029

## Implementation Plan

1. Write the feature file and failing tests for metric selection, null rates, auth and merge-safe writes.
2. Constants, domain, gateway, migration, store, service, route.
3. Keep the JWT route's metric tuple and response schema.
4. `make regen-contracts`. Bump `ALEMBIC_HEAD` to `f9a0b1c2d3e4`.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-29 18:20

Ticket opened from the architecture plan.

### 2026-10-29 19:10

Insights read route, media cache, merge-safe snapshot writes, migration
`f9a0b1c2d3e4`, feature file and unit tests are in the working tree. Route
snapshot includes `GET /api/autopilot/ig-insights`. Not committed. Phases 2 and
3 are still open.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- Exclusive `until` / `next_until` instead of an inclusive `next_since`.
- Dashboard and bot share `instagram_post_insights`, but each save names the columns it fetched.
- Media list budget is 4 pages, separate from the 10 insight reads.
- `boost` is null until AE-0574.

## Blockers

None for development. Production scoring waits on the scope probe.

## Final Summary

Pending.
