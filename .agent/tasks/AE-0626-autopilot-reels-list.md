# AE-0626 — Autopilot Reels list for the repost scout (GET /reels, /reels/{id}/video)

Status: Review
Tier: T2
Priority: High
Type: Feature
Area: Backend
Owner: Claude
Agent Lane: architect → developer → qa → release
Branch: feat/autopilot-reels-repost
Created: 2026-11-19
Updated: 2026-11-19

## Goal

GrokBot Scout can list Pedro's past Reels with metrics, rates, a baseline and their last repost, so it can pick one to
repost. It can also stream a Reel's MP4 without depending on an expiring CDN URL.

## Problem

`GET /api/autopilot/ig-insights` covers 90 days at most, keeps only a 280-character caption excerpt, and never returns
media URLs, shortcodes, durations, collaborators or repost history. The scout needs all of these to pick a Reel and
download its video (spec "Reels repost API v1" §1, §1b; ADR-0031).

## Scope

- `GET /api/autopilot/reels` with `min_age_days` (60), `max_age_days` (730), `limit` (50, max 100), `cursor`,
  `sort` (`views_desc` | `shares_rate_desc` | `timestamp_desc`) and `exclude_reposted_days` (90).
- A Graph walk of `/{ig-user-id}/media` with `id,media_type,media_product_type,permalink,shortcode,timestamp,caption,`
  `media_url,thumbnail_url`, keeping `REELS` only.
- Insights from the existing snapshot table: refreshed when older than 6 h (a bounded number per request), otherwise
  `stale: true`.
- Duration (ffprobe) and collaborators (`/{media-id}/collaborators`), cached in a new `autopilot_reel_facts` table.
- Rates: `shares_per_100_views`, `saves_per_100_reach`, `follows_per_1000_reach`, `engagement_rate` and
  `avg_watch_ratio` (avg watch time / duration).
- `baseline` medians over the Reels in the age window. `last_repost` from `autopilot_reposts`.
- An opaque offset cursor. `video_url_expires_at` parsed from the CDN `oe` parameter.
- `GET /api/autopilot/reels/{media_id}/video` streams `video/mp4`. Answers 404 `reel_not_found`.
- Errors shaped `{"error": {"code","message","field"}}`, with 400 `invalid_field` for a bad query.

## Non-Goals

- Collab Reels where Pedro is only a collaborator (Graph does not list them; see ADR-0031).
- Changing `GET /ig-insights` or the dashboard insights route.

## Acceptance Criteria

- [ ] AC1: Only `REELS` aged between `min_age_days` and `max_age_days` are returned, sorted by `sort`, paged by `limit` /
  `next_cursor`.
- [ ] AC2: Each item carries the spec fields: `metrics`, `rates`, `collaborators`, `duration_s`, `video_url`,
  `video_url_expires_at`, `last_repost`, and `stale` when its snapshot is older than 6 h.
- [ ] AC3: Reels with a live repost created in the last `exclude_reposted_days` days are hidden, and so are Reels that
  are themselves reposts.
- [ ] AC4: A bad query parameter answers 400 `invalid_field` with `field` set.
- [ ] AC5: `/reels/{id}/video` streams `video/mp4` for Pedro's Reel. Any other id answers 404 `reel_not_found`.
- [ ] AC6: Both routes share the 10/min autopilot budget and need the API key.

## Gherkin Scenarios

See `backend/tests/features/autopilot_reels_list_ae0626.feature`.

## Affected Areas

- Backend: `modules/autopilot` (reels domain, gateway, service, routes)
- Database: new table `autopilot_reel_facts`
- API: two new GET routes
- Tests: unit + feature
- Docs: `docs/architecture/grokbot-reels-repost.md`

## Dependencies

- Related: AE-0627, AE-0628, AE-0629, ADR-0031

## Implementation Plan

1. Domain: reel item, query parsing, sort, cursor, rates, baseline, CDN expiry.
2. Infrastructure: Graph reels walk, collaborators, ffprobe, facts store.
3. Service plus routes plus the error envelope.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-19 21:00

Ticket created from spec v1.

### 2026-11-19 23:30

GET /reels and /reels/{id}/video implemented: Graph walk (20 pages × 50), 6 h snapshot refresh capped at 30 per request, ffprobe duration + collaborators cached in `autopilot_reel_facts`, sort/cursor/baseline, repost hiding (originals in window + reposts themselves). Found while testing: `exclude_reposted_days=0` still hid same-second drafts; fixed to hide no originals at 0.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/reels_constants.py`, `domain/reels.py`, `domain/reels_query.py`
- `application/reels_service.py`, `infrastructure/reels_gateway.py`, `infrastructure/graph_json.py`
- `api/reels.py`, `api/repost_mapping.py`, `api/repost_schemas.py`, `api/middleware/rate_limiting.py` (429 envelope)
- `infrastructure/repost_models.py` (`autopilot_reel_facts`), migration `c3d4e5f6a7b9`
- Tests: `test_reels_list_ae0626.py`, `test_repost_graph_ae0629.py` (gateway), `tests/integration/test_autopilot_repost_api_ae0628.py`
- Feature: `tests/features/autopilot_reels_list_ae0626.feature`

## Test Evidence

Local, Python 3.11 (prod), throwaway Postgres 16 for DB gates:

- New tests: 211 (unit + integration) across `test_repost_*`, `test_reel*`, `test_reels_list_ae0626.py`,
  `test_autopilot_repost_api_ae0628.py`, `test_autopilot_reel_cover_api_ae0627.py`. Branch coverage of the new modules:
  99–100 % for domain, application and infrastructure.
- A real ffmpeg render (`test_real_render_end_to_end`, skipped when ffmpeg is missing): h264 1080×1920 with the hook
  drawn. Frames checked by eye.
- Affected suites: 4186 passed (autopilot unit tests, workers, application, route snapshot, cover/migration
  integration).
- Full `backend:test`: 9413 passed. The 14 failures and 13 errors were 10 migration-head tests (fixed:
  `ALEMBIC_HEAD` → `c3d4e5f6a7b9`, chain test extended) plus agent and carousel_consolidation tests that also fail on
  `origin/main` under Python 3.11 locally. Those pass under Python 3.12 (the CI version), and the branch passes them
  under 3.12 too.
- Gates PASS individually: format, lint, lint-diff, blanket-ignore, strict-diff, type, imports, arch-ratchet,
  docstrings, dead-code, inline-prompts, gherkin-refs, comments, blog-v1-dead-code, redis-factory, autopilot-env,
  healthcheck-loopback, openapi-fresh, integrity, duplication (0.40 %), diff-cover, migrations, schema-drift.
  Mutation: CI only (AE-0448).


## QA Report

[AE-0626.qa.md](../reports/AE-0626.qa.md), which points to the wave report [wave-reels-repost.qa.md](../reports/wave-reels-repost.qa.md). External QA (opencode) took 2 rounds and passed on `84bf6e408`; all findings are resolved. Still open in CI: `backend / Test & Coverage` and the backend mutation job.

## Decision Log

See ADR-0031.

## Blockers

None.

## Final Summary

Pending.
