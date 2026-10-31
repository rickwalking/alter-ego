# AE-0579 — Pass the Meta ads variables through the production env

Status: In Development
Tier: T1
Priority: High
Type: Chore
Area: Deploy
Owner: Pedro
Agent Lane: developer → qa → release
Branch: feat/ae-0579-meta-ads-env-passthrough
Kanban Card: TBD
Created: 2026-10-31
Updated: 2026-10-31

## Goal

The approved boost launch (generation worker) and the owner's pause from Telegram (web backend) get the Meta ads
token, ad account, page and Instagram user on prod. Pedro approved spending (D-70p, 2026-10-31).

## Problem

`deploy.yml` and `docker-compose.prod.yml` pass `BOOST_ENABLED` and `BOOST_REQUESTS_ENABLED` (#312), but not
`META_ADS_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_PAGE_ID` or `META_ADS_IG_USER_ID`. Without the token the ads
gateway is never built, so an owner-approved boost cannot launch and a pause cannot reach Meta.

## Scope

- `deploy.yml` writes the four variables from GitHub secrets of the same name.
- `docker-compose.prod.yml` passes each to `backend` and `generation-worker` with an empty default.
- `check_autopilot_env_parity.py` requires the four names on both surfaces (rule-fires: the old `deploy.yml`
  reports all four missing).

No public or user-visible behavior change in code. Until Pedro adds the secrets the values are empty and the launch
path stays inert (`_ads_client` returns no gateway for an empty token).

Secret format: `META_AD_ACCOUNT_ID` is the bare numeric id, **without** the `act_` prefix (the gateway builds
`/act_{account}/...`, so `act_123` would call `/act_act_123`).

## Non-Goals

- Any boost cap: daily R$6-30, R$100 a week, at most 7 days, Brazil only, 12 h approval stay the shipped settings
  defaults; no prod surface sets them (pinned by a test).
- `META_ADS_APP_SECRET` (optional `appsecret_proof`; not requested).
- Adding the secrets (Pedro does that).

## Acceptance Criteria

- [ ] AC1 `deploy.yml` writes each of the four variables from its secret.
- [ ] AC2 `backend` and `generation-worker` receive each with an empty default.
- [ ] AC3 The env parity check requires the four names and fires when one is missing.
- [ ] AC4 No prod surface sets a boost cap.
- [ ] AC5 After deploy, a read-only prod check reports the four as present/absent booleans and whether the ads
  gateway is built; no boost is created.

## Gherkin Scenarios

- `backend/tests/features/meta_ads_env_ae0579.feature`

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [x] Tests
- [x] Deploy workflow

## Dependencies

AE-0572 / #312 (boost switches passthrough).

## Progress Log

### 2026-10-31 12:10

Passthrough, parity names and tests written. Parity check on the old `deploy.yml`: 4 missing (exit 1); the new
services test on the old compose: 2 failed.

## Files Touched

- `.github/workflows/deploy.yml`
- `docker-compose.prod.yml`
- `scripts/ci/check_autopilot_env_parity.py`
- `backend/tests/unit/scripts_ci/test_check_autopilot_env_parity.py`
- `backend/tests/unit/scripts_ci/test_meta_ads_env_ae0579.py`
- `backend/tests/features/meta_ads_env_ae0579.feature`

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
