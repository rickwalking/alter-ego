# AE-0591 — Boost ad set sends the capped audience and run window, and keeps Meta's error details

Status: Dev Complete
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0591-boost-meta-payload
Kanban Card: TBD
Created: 2026-11-01
Updated: 2026-11-01

## Goal

An approved boost reaches Meta with an ad set that carries the stored audience and a start and end time, so the
shipped caps hold on Meta's side too. Every Marketing API failure keeps which call failed and Meta's own error
fields (never the token), and a validate-only command lets the owner check a request's real bodies without creating
anything (Pedro's decision, 2026-11-01).

## Problem

Both owner-approved boost requests failed with `meta_100`. The read-only and `validate_only` diagnosis on prod
(Graph v23.0, 2026-11-01) found:

1. The media preflight `GET /{media_id}?fields=id` with the ads token answers 400, code 100, subcode 33
   ("Unsupported get request ... missing permissions"). The ads token has `ads_management`, `pages_manage_ads`,
   `instagram_manage_*` and `business_management`, but not `instagram_basic`. The account and minimum-budget reads
   work, and the campaign body passes `validate_only`.
2. The creative body under `validate_only` answers 400, code 100, subcode 1885183, "Ads creative post was created
   by an app that is in development mode". The Meta app must be switched to Live; this is not a code fix.
3. The ad set body sent no `targeting` and no `start_time`/`end_time`, although every request stores
   `audience` = `{"countries": ["BR"], "age_min": 18, "age_max": 65}` and `days`, `starts_at`, `ends_at`.
4. `_json` flattened every error to `meta_<code>`; only that code was stored, so the cause was invisible.

## Scope

- Ad set body (`meta_ads_payloads.adset_payload`): `targeting` from the stored audience
  (`geo_locations.countries`, `age_min`, `age_max`), `publisher_platforms=["instagram"]`,
  `instagram_positions=["stream"]` (the Instagram feed, where the boosted post lives) and
  `targeting_automation.advantage_audience=0` (v23 requires the flag explicitly; 0 stops Meta from widening the
  audience past the caps). `start_time`/`end_time` are unix seconds: start is the requested start or now (whichever
  is later), end is start + `days`.
- The caps are checked before any HTTP: countries must be a non-empty subset of `{"BR"}` (`country_not_allowed`),
  ages within 18-65 with `age_min <= age_max` (`audience_invalid`), `days` 1-7 (`days_over_cap`, or
  `boost_schedule_invalid` for 0). All permanent.
- The launched request records the ad set's `starts_at`/`ends_at` (existing columns).
- Campaign, creative and ad bodies are unchanged and moved to the same pure builder module. The creative keeps
  the documented "use an existing Instagram post" form (`object_id` = Page, `instagram_user_id`,
  `source_instagram_media_id`; `instagram_user_id` replaces the deprecated `instagram_actor_id`). The campaign keeps
  `is_adset_budget_sharing_enabled=false` (required when there is no campaign budget).
- Errors (`meta_ads_errors.read_body`): `AdsCallError.detail` holds `call` (`preflight_media`,
  `preflight_account`, `min_budgets`, `campaign`, `adset`, `creative`, `ad`, `activate`, `pause`), `http_status`
  and Meta's `code`, `error_subcode`, `type`, `message`, `error_user_title`, `error_user_msg`, `fbtrace_id` as
  strings, each capped at 500 characters, with the token and appsecret proof replaced by `[redacted]`. The URL is
  never stored.
- Error codes: subcode 1885183 → `meta_app_dev_mode`; code 100 / subcode 33 on the media preflight →
  `meta_media_unreadable`; otherwise `meta_<code>`. 5xx stays `meta_transient` (transient); 4xx stays permanent.
- The worker stores the details on the failure event (`boost_request_events.detail`, existing JSON column; the
  request keeps `error_code`) and logs one structured `boost.launch` warning with them.
- `python -m rag_backend.scripts.boost_validate_only <request_id> [--campaign-id X] [--adset-id Y --creative-id Z]`:
  builds the exact launch bodies through the same builders and signed Graph client, runs the three preflight reads,
  posts the campaign and the creative with `execution_options=["validate_only"]`, and validates the ad set and ad
  only against given existing parent ids (otherwise prints their body, token redacted). A POST without
  `validate_only` is refused before it is sent. One JSON line per call; exit 1 when a sent call failed. The
  entry module loads the ORM model registry before the autopilot package (the app's import order), because the
  autopilot package cannot be the first import of a process (existing circular import through
  `models/autopilot_registry.py`).

### Review fixes (2026-11-01)

- The worker re-checks the caps in force right before launching (`check_launch`: objective, daily budget floor and
  cap, days, audience, and the rolling-week total without the request's own budget). A cap lowered after the
  approval fails the launch permanent (approved → failed) with the existing cap codes and no Meta call.
- The ad set window and targeting use `AdsConfig.caps` built from the settings (`BOOST_MAX_DAYS`,
  `BOOST_ALLOWED_COUNTRIES`; ages stay 18-65, not configurable), not hard-coded values.
- The preflight rules (media visible, account active, budget floor) and `require_page` live in
  `meta_ads_preflight.py`; the launch and the validate-only check run the same rules. The check also reports the
  caps re-check, so anything a launch would fail on is a failed line and exit 1.
- The validate-only check reports `httpx.InvalidURL` by its type name only.
- A test proves no launch POST carries `execution_options`.

## Non-Goals

- No change to the caps (R$6-30/day, R$100/week, max 7 days, Brazil only, 12h approval) or the approval flow.
- No schema change; `starts_at`, `ends_at` and the event `detail` JSON already exist.
- The media preflight is not skipped or switched: it now fails explicitly with `meta_media_unreadable`.
- No change to permanent/transient classification beyond the two specific codes.

## Owner actions (not code)

- Add `instagram_basic` to the ads System User token, or the media preflight keeps failing with
  `meta_media_unreadable`. A follow-up can switch the check to the Instagram token or an ads-side read.
- Switch the Meta app to Live, or every creative fails with `meta_app_dev_mode`.
- Then run `boost_validate_only` on a request before re-approving.

## Acceptance Criteria

- [x] AC1 The ad set body carries `targeting` (Brazil, 18-65, Instagram feed, advantage audience off) and
  `start_time`/`end_time` = start + days.
- [x] AC2 An audience outside Brazil or 18-65, or a run of 0 or more than 7 days, fails permanent before any HTTP.
- [x] AC3 Every failing call raises an `AdsCallError` whose `detail` names the call and carries Meta's fields.
- [x] AC4 Subcode 1885183 → `meta_app_dev_mode`; 100/33 on the media preflight → `meta_media_unreadable`.
- [x] AC5 The token and the appsecret proof never appear in the details or the log.
- [x] AC6 The worker stores the details on the failure event and logs them; the Postgres event `detail` holds them.
- [x] AC7 The validate-only command sends only `validate_only` POSTs; a POST without it is refused unsent.
- [x] AC8 The worker re-checks the caps in force at launch; a lowered cap fails the launch with its cap code.
- [x] AC9 The ad set window and targeting use the configured caps from the settings.
- [x] AC10 The validate-only check applies the launch's preflight rules, Page check and caps; any failure exits 1.
- [x] AC11 No launch POST carries `execution_options`; `httpx.InvalidURL` is reported by type only.

## Gherkin Scenarios

- `backend/tests/features/boost_meta_payload_ae0591.feature`

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None. Builds on AE-0586 (`meta_page_missing`).

## Progress Log

### 2026-11-01

Ticket created from the prod diagnosis. Split the gateway: `meta_graph.py` (config, signed GET/POST, error
reading), `meta_ads_errors.py` (`AdsCallError` with details, code mapping, redaction), `meta_ads_payloads.py`
(pure bodies + cap checks), `meta_ads_constants.py` (call names, Meta fields, targeting keys). The gateway and the
new validate-only check use the same builders and client. `BoostRequest.error_detail` (not a column) carries the
details to `SqlBoostStore`, which merges them into the event `detail` with `error_code`. Tests mock the Graph API
with `httpx.MockTransport`; no Meta call is made.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/meta_ads_constants.py`
- `backend/src/rag_backend/modules/autopilot/boost_constants.py`
- `backend/src/rag_backend/modules/autopilot/domain/boost.py`
- `backend/src/rag_backend/modules/autopilot/application/boost_tick.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/meta_graph.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/meta_ads_errors.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/meta_ads_payloads.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/meta_ads_gateway.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/meta_ads_preflight.py`
- `backend/src/rag_backend/modules/autopilot/domain/boost_policy.py`
- `backend/src/rag_backend/modules/autopilot/application/boost_requests.py`
- `backend/src/rag_backend/modules/autopilot/api/boost.py`
- `backend/src/rag_backend/bootstrap/autopilot_worker_factory.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/boost_store.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/boost_validate_only.py`
- `backend/src/rag_backend/scripts/boost_validate_only.py`
- `backend/src/rag_backend/scripts/boost_validate_only_cli.py`
- `backend/tests/features/boost_meta_payload_ae0591.feature`
- `backend/tests/unit/modules/autopilot/meta_ads_fakes.py`
- `backend/tests/unit/modules/autopilot/test_boost_meta_payload_ae0591.py`
- `backend/tests/unit/modules/autopilot/test_boost_meta_errors_ae0591.py`
- `backend/tests/unit/modules/autopilot/test_boost_validate_only_ae0591.py`
- `backend/tests/unit/modules/autopilot/test_boost_launch_caps_ae0591.py`
- `backend/tests/integration/test_boost_failure_detail_pg_ae0591.py`

## Test Evidence

Review-fix rerun at dfc0f5ba2 (hotfix fast path, laptop-gate heavy): every backend gate except mutation, individually, Postgres-backed: 8151 passed, 2 skipped; diff-cover 99% on changed lines; integrity 0 net-new blockers; Python 3.11.15 import check ok. The first migrations/schema-drift attempt failed on local test-DB state only (alembic_version stamped to an empty `_driftcheck` revision left by the earlier run); restamped to head `b9c0d1e2f3a4` and both reran green. mutation: deferred to CI (hotfix fast path).

GATES_JSON: {"pass":26,"fail":0,"skip":1,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:gherkin-refs","status":"PASS"},{"gate":"backend:comments","status":"PASS"},{"gate":"backend:blog-v1-dead-code","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:openapi-fresh","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:duplication","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:mutation","status":"SKIP"}]}

Earlier run at 2e70da495: Hotfix fast path: every backend gate except mutation run individually (Postgres-backed) at 2e70da495:
8135 passed, 2 skipped; diff-cover 98% on changed lines. Python 3.11.15 import check ok. Integrity: 0 net-new
blockers. mutation: deferred to CI (hotfix fast path).



## QA Report

TBD

## Blockers

None.

## Final Summary

TBD
