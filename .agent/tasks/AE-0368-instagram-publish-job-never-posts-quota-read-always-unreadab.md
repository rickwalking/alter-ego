# AE-0368 — Instagram publish job never posts: quota read always unreadable

Status: Intake
Tier: T1
Priority: P0
Type: Bugfix
Area: backend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0368-instagram-quota-fields
Created: 2026-10-14
Updated: 2026-10-14
Parent: AE-0348

## Goal

The autopilot publish job reads the Instagram publishing quota correctly and posts the approved
carousel, and a quota it cannot read ends the run as `publish_failed` instead of looping.

## Problem

Prod 2026-10-14: after the owner's Telegram Approve the run sat in `publishing` with
`state_reason=content_publishing_limit_unreadable` and made no post attempt (the carousel was
published by hand).

- `MetaInstagramPublisher.content_publishing_remaining` called
  `GET /{ig_user_id}/content_publishing_limit` without `fields`.
- Verified live on `graph.instagram.com/v23.0`: without `fields` the body is
  `{"data":[{"quota_usage":0}]}`; with `fields=quota_usage,config` it is
  `{"data":[{"quota_usage":0,"config":{"quota_total":100,"quota_duration":86400}}]}`.
- `quota_remaining()` required `config.quota_total`, so every read raised the transient
  `content_publishing_limit_unreadable`.

## Scope

- Send `fields=quota_usage,config` (`PUBLISHING_LIMIT_FIELDS`) on the quota GET.
- Parser: a readable `quota_usage` without a usable `config.quota_total` falls back to Meta's
  documented 100 posts / 24 h (`DEFAULT_PUBLISHING_QUOTA_TOTAL`) and logs
  `instagram_quota_total_missing`. A body without a readable `quota_usage` still fails closed.
- Loop guard: reuse the existing publish retry budget (`PUBLISH_MAX_ATTEMPTS` = 3, backoff 60 s
  then 300 s). A transient quota error is recorded as an attempt; the third one moves the run to
  `publish_failed` and sends the existing publish-failed notice (with Retry). Covered by a new
  end-to-end test through the real gateway and publisher.
- Sweep of the other Graph GETs for missing `fields`.

## Non-Goals

- Do not refactor unrelated code.
- No migration. Nothing run against prod; no prod data touched.

## Acceptance Criteria

- [x] The quota GET carries `fields=quota_usage,config` (respx test, live body shape).
- [x] Live body with `config` → `quota_total - quota_usage`.
- [x] Live body without `config` → falls back to 100, warning logged, the job publishes.
- [x] Unreadable usage (empty data, bool, string, missing) → transient
  `content_publishing_limit_unreadable`.
- [x] Unreadable quota on 3 ticks past the backoff → `publish_failed` + owner notice, no
  container created.
- [x] Gherkin scenarios in `backend/tests/features/autopilot_instagram_publish.feature`.
- [x] Other Graph GETs swept.
- [x] Python 3.11 import check.

## Repro Steps

1. A run reaches `publishing` with a real Graph publisher on `graph.instagram.com/v23.0`.
2. Before the fix: every tick reads the limit without `fields`, gets no `config`, and records
   `content_publishing_limit_unreadable`; no container is created.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Graph GET sweep (requirement 5)

- `container_status` (`/{container_id}`): sends `fields=status_code`. OK.
- `fetch_permalink` (`/{media_id}`): sends `fields=permalink`. OK.
- `recover_published_media` (`/{ig_user_id}/media`): sends `fields=id,media_type,timestamp` and
  `limit`. OK.
- `content_publishing_limit`: was missing `fields`. Fixed.
- `instagram_token_client` (`graph.instagram.com/refresh_access_token`): not a node read;
  `access_token` / `expires_in` come back by default. OK.

## Progress Log

### 2026-10-14

Ticket created from the prod incident. Fix, tests, Gherkin. Hotfix fast path gates (mutation
deferred to CI) and the Python 3.11 import check; see the dev summary.

## Files Touched

- `backend/src/rag_backend/domain/constants/instagram_publish.py`
- `backend/src/rag_backend/infrastructure/external/meta_instagram_publisher.py`
- `backend/src/rag_backend/infrastructure/external/instagram_graph_payloads.py`
- `backend/tests/unit/modules/autopilot/test_instagram_quota_ae0368.py` (new)
- `backend/tests/features/autopilot_instagram_publish.feature`

## Test Evidence

See `.agent/reports/AE-0368.dev-summary.md` (GATES_JSON line).

## QA Report

Pending.

## Blockers

None.
