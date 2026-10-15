# AE-0378 — Instagram insights on the dashboard and the analytics load error

Status: Ready
Tier: T2
Priority: Medium
Type: Feature
Area: Cross-cutting
Owner: Claude (autonomous worker)
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0371-growth-pov-mode
Kanban Card: TBD
Parent: AE-0371
Created: 2026-10-15
Updated: 2026-10-15

## Goal

Show per-post Instagram insights on the dashboard to feed the plan's KPIs, and stop the analytics card from failing the dashboard (roadmap R8).

## Problem

There is no Instagram insights code; the dashboard's analytics card shows "Failed to load analytics" whenever `/api/editorial-analytics` is not OK (feature flag off, role, rate limit).

## Scope

- Insights gateway (Graph `/{media-id}/insights`), snapshot table, refresh service (6 h TTL), `GET /api/instagram/insights`.
- Dashboard Instagram KPI card (views, reach, shares, saves, follows, profile visits; follows per post; shares per 100 views); "n/d" for missing metrics.
- Editorial analytics card: explicit disabled state when the flag is off.

## Non-Goals

- Account-level demographics, non-follower share per post (not offered per media by the Graph API; shown as n/d).
- Third-party analytics tools.

## Acceptance Criteria

- [ ] WHEN the dashboard asks for insights THE SYSTEM SHALL return one row per published post with the stored metrics and ratios.
- [ ] WHEN a snapshot is older than 6 h THE SYSTEM SHALL refresh it from the Graph API; a Graph failure SHALL keep the last snapshot and flag the row stale.
- [ ] WHEN the Graph API omits a metric THE SYSTEM SHALL return null and the UI SHALL show "n/d", never an estimate.
- [ ] WHEN the editorial-analytics flag is off THE dashboard SHALL show a disabled state instead of "Failed to load analytics".

## Gherkin Scenarios

```gherkin
Feature: Instagram insights

  Scenario: Fresh insights for published posts
    Given two published posts without snapshots
    When the insights are requested
    Then each post has its views, shares, saves and follows

  Scenario: Graph failure keeps the last snapshot
    Given a stale snapshot and a failing Graph API
    When the insights are requested
    Then the old values are returned and marked stale

  Scenario: Missing metric
    Given the Graph API does not return follows for a post
    When the insights are requested
    Then follows is null and the card shows n/d

  Scenario: Analytics flag off
    Given the editorial analytics route answers 404
    When the dashboard loads
    Then the analytics card shows the disabled state
```

## Delta

### ADDED

- Insights gateway (Graph `/{media-id}/insights`), snapshot table, refresh service (6 h TTL), `GET /api/instagram/insights`.
- Dashboard Instagram KPI card (views, reach, shares, saves, follows, profile visits; follows per post; shares per 100 views); "n/d" for missing metrics.
- Editorial analytics card: explicit disabled state when the flag is off.

### MODIFIED

- See Scope.

### REMOVED

- None.

## Affected Areas

- Backend: new insights module under modules/autopilot (reuses Graph client)
- Frontend: dashboard page, new KPI card, analytics hook
- Database: new table instagram_post_insights
- API: GET /api/instagram/insights
- Tests: unit + `instagram_insights.feature` + vitest
- Docs: plan §D11
- Prompts/LLM: none
- Observability: structlog events
- Deployment: manual SQL

## Dependencies

- Blocks: none
- Blocked by: AE-0377
- Related: AE-0371

## Implementation Plan

1. Gherkin
2. gateway + store + migration
3. route
4. frontend

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-15 10:00

Ticket written from the architect plan (docs/architecture/instagram-growth-pov-mode.md).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- 2026-10-15: design per ADR-0021 and the architect plan; see the epic AE-0371 Decision Log for cross-cutting decisions.

## Blockers

None.

## Final Summary

Pending.
