# AE-0627 — `purpose=reel_cover` on POST /api/autopilot/assets

Status: In Development
Tier: T2
Priority: High
Type: Feature
Area: Backend
Owner: Claude
Agent Lane: developer → qa → release
Branch: feat/autopilot-reels-repost
Created: 2026-11-19
Updated: 2026-11-19

## Goal

GrokBot can upload a 1080×1920 Reel cover through the existing asset route and use it once on a repost draft.

## Problem

`POST /assets` accepts only carousel slide-1 covers (cropped to 4:5, 1080×1350). A Reel cover is 9:16 and may carry title
text (spec §2 "Changes to POST /api/autopilot/assets").

## Scope

- A new form field `purpose`: `carousel_cover` (the default, unchanged behaviour) or `reel_cover`.
- `reel_cover` requires `kind=ai_image` and a 9:16 image of at least 1080×1920. It is scaled to exactly 1080×1920 and
  never cropped. A wrong purpose answers 422 `asset_purpose_invalid`.
- The cover row stores `purpose` and `repost_id`. A reel cover cannot be used on a carousel topic, and a carousel cover
  cannot be used on a repost.
- The 6 h sweep skips covers a repost has claimed.

## Non-Goals

- Automated detection of logos or other people (a policy rule for the scout, as for carousel covers).

## Acceptance Criteria

- [ ] AC1: With no `purpose`, the upload behaves exactly as before.
- [ ] AC2: `purpose=reel_cover` with a 1080×1920 PNG or JPEG answers 201 with `width=1080, height=1920`.
- [ ] AC3: A reel cover that is not 9:16, is smaller than 1080×1920, or is not `kind=ai_image` is refused (422).
- [ ] AC4: An unknown `purpose` answers 422 `asset_purpose_invalid`.
- [ ] AC5: A topic that names a reel cover is refused with `cover_asset_unknown`.

## Gherkin Scenarios

See `backend/tests/features/reel_cover_asset_ae0627.feature`.

## Affected Areas

- Backend: cover upload, cover validation, cover store
- Database: `autopilot_cover_assets.purpose`, `autopilot_cover_assets.repost_id`
- API: `POST /api/autopilot/assets` (additive field)

## Dependencies

- Related: AE-0628, ADR-0024, ADR-0031

## Implementation Plan

1. Constants and validation for 9:16.
2. Form field, cover row columns and the migration.
3. Topic-side guard.

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

`purpose` form field added (default `carousel_cover`, unchanged behaviour). Reel covers must be 9:16 within 1 % and ≥1080×1920, scaled (never cropped). Topics refuse reel covers; drafts refuse carousel covers.

## Files Touched

- `domain/constants/slide_cover.py`, `application/services/carousel/cover_asset_validation.py` (9:16, scale to 1080×1920)
- `modules/editorial/infrastructure/carousel_cover.py`, `modules/autopilot/domain/cover.py`, `domain/cover_ports.py`
- `application/cover_upload.py`, `api/assets.py`, `api/schemas.py`, `cover_constants.py`
- `infrastructure/cover_models.py`, `infrastructure/cover_store.py` (`purpose`, `repost_id`, `claim_for_repost`, sweep skips claimed)
- Tests: `test_reel_cover_ae0627.py`, `tests/integration/test_autopilot_reel_cover_api_ae0627.py`, `test_repost_store_ae0628.py`
- Feature: `tests/features/reel_cover_asset_ae0627.feature`

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

[AE-0627.qa.md](../reports/AE-0627.qa.md), which points to the wave report [wave-reels-repost.qa.md](../reports/wave-reels-repost.qa.md). External QA (opencode) took 2 rounds and passed on `84bf6e408`; all findings are resolved. Still open in CI: `backend / Test & Coverage` and the backend mutation job.

## Decision Log

See ADR-0031.

## Blockers

None.

## Final Summary

Pending.
