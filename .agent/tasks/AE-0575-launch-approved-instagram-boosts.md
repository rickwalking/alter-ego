# AE-0575 — Launch approved Instagram boosts

Status: Ready
Tier: T3
Priority: P1
Type: Feature
Area: backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: feat/ae-0575-boost-launch
Kanban Card: TBD
Parent: AE-0572
Created: 2026-10-29
Updated: 2026-10-29

## Goal

After the owner has approved a boost request, the worker creates the Meta campaign paused, stores each id, and activates it only while `BOOST_ENABLED` is true. The API key still cannot start or stop spend. A crash mid-launch resumes without a second campaign.

## Problem

Phase 2 records the owner's yes and then stops. Spend needs a separate ads token, a resumable create sequence, and a kill switch that is off unless someone turns it on.

## Scope

Implement phase 3 of `.agent/reports/AE-0572.arch-plan.md`:

- `MetaAdsGateway` used only from the boost tick.
- Preflight (media visible, account active, currency match, Meta minimum daily budget).
- Paused campaign, ad set, creative and ad; persist ids; activate last.
- Retry classification, audit events, hourly ad insights, completion, owner Stop (`ap:bst:stop:`).
- Settings `META_ADS_ACCESS_TOKEN`, `META_ADS_APP_SECRET`, `META_AD_ACCOUNT_ID`, `META_PAGE_ID`, `META_ADS_IG_USER_ID`, `META_ADS_GRAPH_BASE` (default `GRAPH_HOST_FACEBOOK`), `BOOST_INSIGHTS_POLL_MINUTES`, `BOOST_LAUNCH_MAX_ATTEMPTS`.
- Redact `appsecret_proof` as well as `access_token`.
- Env parity for the new names. `BOOST_ENABLED` stays default false.

## Non-Goals

- Any Marketing API call from an `X-Api-Key` route.
- Auto-pausing ads that are already active when the kill switch is turned off. The owner uses Stop or Ads Manager.
- Awareness objective, Advantage+ audiences left on, or new creatives.
- Encrypting the ads token into `integration_credentials`.
- Accepting ADR-0029 inside the code change. A human accepts the ADR before production spend.

## Acceptance Criteria

- [ ] WHEN `BOOST_ENABLED` is false THE worker SHALL make zero Marketing API calls, including when an approved row exists.
- [ ] WHEN an approved request is launched THE campaign, ad set, creative and ad SHALL be created `PAUSED`, each id stored before the next step, then activated.
- [ ] WHEN the process crashes after any stored id THE next tick SHALL skip that step AND SHALL NOT create a duplicate object.
- [ ] WHEN Meta returns a permanent error THE row SHALL be `failed`, created objects paused, and the owner notified. `error_code` SHALL be `meta_<code>_<subcode>` with no raw token.
- [ ] WHEN the ad account minimum daily budget is above the request THE launch SHALL fail with `below_meta_minimum` before creating a campaign.
- [ ] WHEN the ads token cannot read the media id THE row SHALL fail with `media_not_visible_to_ads`.
- [ ] WHEN an active ad passes `ends_at` THE row SHALL become `completed` after a final insights read.
- [ ] WHEN the owner taps Stop on an active boost THE campaign SHALL be paused AND the status SHALL be `stopped`.
- [ ] No log line, API response or audit row contains the access token or `appsecret_proof`.
- [ ] `GET /api/autopilot/boost-request/{id}` returns stored `last_insights` and does not call Meta.
- [ ] Env parity passes. Production defaults leave `BOOST_ENABLED` false.

## Gherkin Scenarios

```gherkin
Feature: Launch owner-approved Instagram boosts

  Scenario: Kill switch blocks spending
    Given BOOST_ENABLED is false
    And an approved boost request exists
    When the worker ticks
    Then no Marketing API request is made
    And the status is still approved

  Scenario: Paused create then activate
    Given BOOST_ENABLED is true
    And an approved engagement request for a visible feed post
    When the worker ticks
    Then the campaign, ad set, creative and ad are created paused
    And each id is stored before the next create
    And the ad is activated last
    And the status is active

  Scenario: Resume does not duplicate
    Given a launching request that already has a campaign id
    When the worker ticks
    Then no second campaign is created
    And the launch continues at the ad set

  Scenario: Permanent Meta error
    Given Meta rejects the ad set with a permanent error code
    When the worker ticks
    Then the status is failed
    And the campaign is paused
    And the owner is notified
```

## Delta

### ADDED

- Ads gateway, launch and insights steps on the existing boost tick, Stop callback.
- Ads settings and env parity entries.
- `appsecret_proof` redaction.
- Tests listed in the architecture plan's phase 3 section.

### MODIFIED

- `boost_tick` gains the launch branch.
- `boost_constants` payload values that the test account must confirm.
- Log redaction patterns.

### REMOVED

- None.

## Affected Areas

- Backend: autopilot boost worker and ads gateway
- Frontend: none
- Database: none (columns already exist from AE-0574)
- API: no new public route. Stop is a Telegram callback.
- Tests: respx gateway, webhook stop, kill-switch call count, log scan
- Docs: ADR-0029 stays proposed until a human accepts it. Note the runbook line that the kill switch does not pause ads already active.
- Prompts/LLM: none
- Observability: `boost.launch`, `boost.insights`, audit rows
- Deployment: GitHub secrets for the ads token and ids. Switch remains false.

## Dependencies

- Blocks: live boosts from the external bot
- Blocked by: AE-0574, ADR-0029 acceptance before `BOOST_ENABLED=true`, Meta checklist in the architecture plan
- Related: ADR-0020, ADR-0029

## Implementation Plan

1. Gateway tests for order, resume, classification and the kill switch, with respx.
2. Preflight, then paused creates, then activate.
3. Insights poll and completion.
4. Stop callback.
5. Confirm unverified payload constants on a test ad account before any production secret is set. If Meta rejects `special_ad_categories`, advantage-audience or positions, change `boost_constants.py` only.
6. Do not flip `BOOST_ENABLED` in `deploy.yml` or compose defaults.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-29 18:20

Ticket opened from the architecture plan. No ads calls until the kill switch is on.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- Test-account confirmation is required for `special_ad_categories`, `targeting_automation.advantage_audience`, and Instagram positions. Those values are constants, not scattered strings.
- `min_daily_budget_high_freq` from `GET /act_{id}/minimum_budgets` is the Meta floor. The product floor remains 600 cents.
- Kill switch off does not pause an already active campaign. Stop does.
- Ads graph base defaults to the existing `GRAPH_HOST_FACEBOOK` constant (`https://graph.facebook.com/v23.0`).

## Blockers

ADR-0029 is proposed. Accept it before enabling spend. Meta checklist is in the architecture plan.

## Final Summary

Pending.
