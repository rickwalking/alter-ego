# AE-0586 — Boost fails fast with meta_page_missing when the Page or Instagram user id is empty

Status: Ready
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

- [ ] AC1 With an empty Page id, `launch` raises a permanent `meta_page_missing` and makes no HTTP request.
- [ ] AC2 With an empty (or blank) Instagram user id, `launch` raises a permanent `meta_page_missing` and makes no
  HTTP request.
- [ ] AC3 The worker tick stores the approved request as `failed` with `error_code=meta_page_missing`.
- [ ] AC4 With both ids set, `launch` still runs the preflight and creates the objects as before.
- [ ] AC5 The kill switch still wins: a disabled gateway raises `ads_disabled` even when the ids are empty.

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

Ticket created.

## Files Touched

TBD

## Test Evidence

TBD

## QA Report

TBD

## Blockers

None.

## Final Summary

TBD
