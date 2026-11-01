# AE-0586 — Boost fails fast with meta_page_missing when the Page or Instagram user id is empty

Status: Dev Complete
Tier: T1
Priority: Low
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0586-meta-page-missing
Kanban Card: TBD
Created: 2026-10-31
Updated: 2026-10-31

## Goal

Launching an approved boost fails at once with the permanent error `meta_page_missing` when the Meta Page id
(`META_PAGE_ID`) or the Instagram user id for ads (`META_ADS_IG_USER_ID`) is empty, before any Marketing API call
(Pedro's decision, 2026-10-31).

## Problem

Meta needs a Facebook Page linked to the Instagram account to boost an Instagram post. Both ids default to `""` in
settings. With an empty value, `MetaAdsGateway.launch` still runs the preflight reads and creates a paused campaign and
ad set on the ad account, then the ad creative call fails with a generic Meta error (`meta_<code>`, or
`meta_transient` on a 5xx). The request ends `failed` with a code that does not say what is missing, and paused
objects are left on the ad account.

## Scope

- New constant `ERR_PAGE_MISSING = "meta_page_missing"` in `boost_constants.py`.
- `MetaAdsGateway.launch` raises `AdsCallError(ERR_PAGE_MISSING, permanent=True)` after the kill-switch check and
  before the preflight when `page_id` or `ig_user_id` is empty or blank.
- The worker tick already stores any launch error as `status=failed` with `error_code`, which the bot reads on
  `GET /api/autopilot/boost-request/{id}` and the list route; the new code reaches it unchanged.

## Non-Goals

- No change to the caps (R$6-30/day, R$100/week, max 7 days, Brazil only, 12h approval) or the approval flow.
- No schema change, no new Telegram notice, no change to `pause`.
- Identity/admin files (`admin_handlers.py`, `user_repository.py`) are owned by another ticket.

## Acceptance Criteria

- [x] AC1 With an empty Page id, `launch` raises a permanent `meta_page_missing` and makes no HTTP request.
- [x] AC2 With an empty (or blank) Instagram user id, `launch` raises a permanent `meta_page_missing` and makes no
  HTTP request.
- [x] AC3 The worker tick stores the approved request as `failed` with `error_code=meta_page_missing`.
- [x] AC4 With both ids set, `launch` still runs the preflight and creates the objects as before.
- [x] AC5 The kill switch still wins: a disabled gateway raises `ads_disabled` even when the ids are empty.

## Gherkin Scenarios

- `backend/tests/features/boost_meta_page_missing_ae0586.feature`

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-31

Ticket created. Traced the boost launch: `BoostTick._launch` calls `MetaAdsGateway.launch`, and any `AdsCallError`
is stored as `failed` with its `error_code` (read by the bot on the boost-request routes). With an empty Page or
Instagram user id the launch made the three preflight reads and created a paused campaign and ad set before the
creative call failed with a generic Meta code. Added `_require_page` after the kill-switch check and before the
preflight, raising a permanent `meta_page_missing`. Five Gherkin-referenced unit tests mock the Graph API with
`httpx.MockTransport` (no Meta calls). First full gate run failed `backend:integrity` on a `type: ignore` in the test
store fake; replaced with a fake that implements the full `BoostStore` protocol, and the second full run is green.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/boost_constants.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/meta_ads_gateway.py`
- `backend/tests/features/boost_meta_page_missing_ae0586.feature`
- `backend/tests/unit/modules/autopilot/test_boost_meta_page_missing_ae0586.py`

## Test Evidence

Full local backend gates at 1a0f7cf44 (Postgres-backed, 8034 passed, 2 skipped; diff-cover 100% on both changed
source files). Mutation runs in CI only.

GATES_JSON: {"pass":26,"fail":0,"skip":1,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:gherkin-refs","status":"PASS"},{"gate":"backend:comments","status":"PASS"},{"gate":"backend:blog-v1-dead-code","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:openapi-fresh","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:duplication","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:mutation","status":"SKIP"}]}

## QA Report

TBD

## Blockers

None.

## Final Summary

TBD
