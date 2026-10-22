# AE-0497 — Analytics "quality score" shows real data or nothing

Status: Review
Tier: T2
Priority: Medium
Type: Bug
Area: Backend + Frontend
Owner: Pedro Marins
Branch: fix/ae-0497-quality-score-real-data
Created: 2026-10-22
Updated: 2026-10-22

## Goal

The "Quality score" tile on `/dashboard/analytics` and on the dashboard home shows the average of real
content quality scores and how many there are, or "Sem dados" when there are none, never an invented
number.

## Problem

Dashboard QA (DQ-B-02): the tile showed a percentage nobody measured.
`EditorialAnalyticsService._estimate_quality_score` averaged `ai_generation_metadata.quality_score` of the
blog posts (nothing writes that key), and when there was none it returned the **share of published posts**
×100 as the "quality score" — or `0.0` with no posts, rendered "0%".

## Scope (TRIAGE Q2 recommendation (a), listed as start-now in the triage)

- The summary's `quality_score_average` is the average `overall_score` (0–100) of the rows in
  `rubric_evaluation_scores` that belong to a piece of content, with the new `quality_score_count` (how
  many). With no such row it is `null` and the count `0`. The published-ratio fallback and the unused
  `ai_generation_metadata.quality_score` read are removed.
- Ad-hoc evaluations of pasted text (`POST /api/rubrics/{id}/evaluate` stores them with the nil content
  id) are not content scores and are left out. Content-linked scores start with AE-0504.
- Both tiles show "Sem dados" / "No data" for `null`, else `NN%` with "n avaliações" / "n evaluations".

## Non-Goals

- Producing rubric scores for carousels (AE-0504).
- Other analytics changes (AE-0500).

## Acceptance Criteria

- [x] Given no content quality scores, Then both tiles show "Sem dados" (not 0%), and the API returns
      `quality_score_average: null`, `quality_score_count: 0`, even when posts are published.
- [x] Given content quality scores exist, Then the tiles show their average and the count behind it.
- [x] The published-ratio fallback is removed; ad-hoc evaluations (nil content id) are not counted.

## Gherkin Scenarios

See `backend/tests/features/analytics_quality_score_ae0497.feature` and
`frontend/tests/features/analytics-quality-score-ae0497.feature`.

## Affected Areas

- [x] Backend (`editorial_analytics_service.py`, publishing projection + ACL, analytics schema)
- [x] Frontend (`dashboard-analytics.tsx`, `analytics/page.tsx`, hook types, i18n)
- [x] API (`quality_score_average` nullable, new `quality_score_count`; OpenAPI artifact, snapshot)
- [x] Tests
- Database: no change.

## Dependencies

- Related: AE-0504 (content rubric scores), AE-0500 (analytics scope).

## Progress Log

### 2026-10-22

Cause confirmed in the code; failing tests first.

## Files Touched

- backend: editorial_analytics_service.py, publishing read_projection_helpers.py / publishing_read_acl.py /
  domain/projections.py, api/schemas/content_quality.py, api/routes/blog_post_quality.py; analytics snapshot;
  openapi.json; unit test + feature (new)
- frontend: modules/editorial-operations/analytics/quality-score.ts (new) + barrel + hook types,
  components/molecules/neon-stat-card.tsx, app/dashboard/dashboard-analytics.tsx, app/dashboard/analytics/page.tsx,
  i18n en/pt, tests + feature

## Test Evidence

Red first (4 backend tests), green after; backend capture and frontend gates green. See `.agent/reports/AE-0497.dev-summary.md`.

## QA Report

External QA: WARN (CI-decided gates only), see `.agent/reports/AE-0497.qa.md`.

## Blockers

None.
