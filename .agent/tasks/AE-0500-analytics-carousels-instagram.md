# AE-0500 — Analytics shows carousel publishing and Instagram insights

Status: In Development
Tier: T2
Priority: Medium
Type: Feature
Area: Backend + Frontend
Owner: Pedro Marins
Branch: feat/ae-0500-analytics-carousels-instagram
Created: 2026-10-30
Updated: 2026-10-30

## Goal

The analytics surfaces (dashboard home and `/dashboard/analytics`) count published carousels — not only
blog posts — in "Publicados" and in the velocity chart, broken down per channel, and the analytics page
shows Instagram insights (totals and per-post rows with `fetched_at`) with an explicit connector state
instead of silent zeros.

## Problem

Dashboard QA (DQ-B-01, DQ-B-03): "Publicados" and the publish-velocity chart were computed only from
`blog_posts.published_at`. Carousels published to Instagram (autopilot runs and manual publishes) were
invisible in analytics, and the Instagram insights KPIs lived only on the dashboard home, never on the
analytics page. The Instagram connector state (not configured / stale / failing) was only a small line
inside the home card, so a dead connector looked like zeros.

## Scope (Pedro's Q1 decision in TRIAGE: blog + carousel publishing counts + Instagram insights)

- A carousel counts as published for the "carousel" channel when it has an Instagram publish record:
  an autopilot run with `ig_post_id` set, or a manual-publish ledger row with `ig_post_id` (the same
  source the insights store uses). The publish time is the run's `updated_at` (stamped at the
  PUBLISHED transition) or the manual record's `claimed_at` — weekly-bucket granularity, matching the
  insights store's ordering timestamps. A public-release carousel (`is_public`) without an Instagram
  publish record is not counted in this channel.
- Publishing counts are channel-pluggable: a counter registry (`blog`, `carousel`) aggregates published
  events per channel; a future LinkedIn or TikTok channel slots in by adding one counter (the LinkedIn
  connector itself is a separate ticket, out of scope here).
- `GET /api/editorial-analytics`: `published_this_week` / `published_this_month` become cross-channel
  sums; the summary gains `channels: [{channel, published_total, published_this_week,
  published_this_month}]`; each velocity week gains `channels: {channel: count}`. Owner/admin scoping
  is unchanged (admin sees all, editor sees own author id / carousel owner id).
- `GET /api/instagram/insights` gains a `connector` block: `{channel, configured, last_sync_at, stale,
  error}` — `last_sync_at` is the newest `fetched_at` over the rows, `stale` applies the existing
  6-hour TTL, `error` is the first Graph error code seen during the request's refresh (null on
  success). The top-level `configured` stays for compatibility.
- The analytics page renders: channel tabs on the velocity chart (Todos / Blog / Carrosséis), a
  per-channel totals line, and an Instagram insights section (totals over views, reach, shares, saves,
  follows, profile visits; per-post rows with `fetched_at`; connector-state banner).

## Non-Goals

- The LinkedIn API connector (separate ticket; Pedro creates/authorizes the LinkedIn app).
- TikTok insights (future channel, same pluggable seam).
- Background/scheduled insight sync (the existing lazy per-request refresh stays).

## Acceptance Criteria

- [ ] Given published carousels, Then "Publicados" and the velocity chart count them per channel (blog,
      carousel), not only blog posts.
- [ ] Given `GET /api/instagram/insights` is configured, Then the page shows views, reach, shares,
      saves, follows, profile visits totals and per-post rows with `fetched_at`, matching the API
      within rounding.
- [ ] Given the connector is not configured or stale, Then the page says so (connector name, last
      sync, error) instead of zeros.
- [ ] Given `average_views`, Then it is removed from the API (OpenAPI artifact, snapshot and every
      consumer updated; no dead field).
- [ ] pt/en strings, keyboard accessible, `:focus-visible` on interactive elements, no colour-only
      meaning.
- [ ] Owner/admin scoping holds for the changed analytics endpoint (editor sees only own content).

## Gherkin Scenarios

See `backend/tests/features/analytics_publishing_channels_ae0500.feature`,
`backend/tests/features/instagram_insights.feature` (connector-status scenarios),
`frontend/tests/features/analytics-channels-ae0500.feature`.

## Affected Areas

- [ ] Backend (`editorial_analytics_service.py` + new channel counters, publishing projection/ACL,
      analytics schemas, instagram insights domain/service/schemas/mapping)
- [ ] Frontend (`analytics/page.tsx` + velocity chart + instagram section, hook types, insights zod
      schema, i18n)
- [ ] API (editorial-analytics response shape, instagram insights `connector` block; OpenAPI artifact,
      snapshot)
- [ ] Tests
- Database: no change.

## Dependencies

- Related: AE-0378 (instagram insights card), AE-0497 (quality score), AE-0504 (content rubric
  scores). Analytics lane: AE-0497 -> AE-0500.

## Progress Log

### 2026-10-30

Ticket created from TRIAGE AE-0500 + Pedro's Q1 analytics decision.

Backend implemented: channel counter registry (`publishing_channels.py`),
per-channel summary/velocity on `GET /api/editorial-analytics`,
`average_views` removed (schema, projection, route, snapshot, OpenAPI), and a
`connector` block on `GET /api/instagram/insights` (channel, configured,
last_sync_at, stale, error). Frontend implemented: velocity channel picker,
per-channel totals line, Instagram insights section (totals, per-post table
with fetched_at, connector-state banners), shared KPI tiles + card shell,
pt/en strings.

## Files Touched

- `backend/src/rag_backend/modules/publishing/infrastructure/publishing_channels.py`
  (new, strictly type-checked: channel counter registry + aggregation)
- `backend/src/rag_backend/application/services/editorial_analytics_service.py`
  (legacy blog-status fields only)
- `backend/src/rag_backend/modules/publishing/constants.py` (channel ids)
- `backend/src/rag_backend/modules/publishing/domain/projections.py`
- `backend/src/rag_backend/modules/publishing/infrastructure/publishing_read_acl.py`
- `backend/src/rag_backend/api/schemas/content_quality.py`
- `backend/src/rag_backend/api/routes/blog_post_quality.py`
- `backend/src/rag_backend/modules/autopilot/{domain/insights.py, application/insights_service.py, api/schemas.py, api/insights_mapping.py, insights_constants.py}`
- `backend/tests/features/analytics_publishing_channels_ae0500.feature` (new),
  `instagram_insights.feature` (connector scenarios), unit + integration tests,
  snapshot, `docs/architecture/openapi.json`
- `frontend/src/app/dashboard/analytics/{page.tsx, velocity-chart.tsx,
  instagram-insights-section.tsx, analytics-page-channels.test.tsx,
  instagram-insights-section.test.tsx}` (new), `instagram-kpi-tiles.tsx`,
  `insights-card-shell.tsx` (new), `instagram-insights-card.tsx`,
  `frontend/src/modules/editorial-operations/analytics/hooks/{types.ts,
  instagram-insights-schema.ts, use-instagram-insights.ts}` + tests, i18n,
  `frontend/src/constants/analytics.ts` (new)
- `docs/decisions/0028-channel-pluggable-publishing-analytics.md` (new)

## Test Evidence

See `.agent/reports/AE-0500.dev-summary.md` — both full gate captures
(backend 22 pass / 0 fail / 5 skip, frontend 18 pass / 0 fail / 1 skip) and
the full backend pytest run (1215 passed).

## Test Evidence

(pending)

## QA Report

(pending)

## Blockers

None.
