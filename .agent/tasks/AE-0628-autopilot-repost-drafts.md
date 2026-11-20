# AE-0628 — Repost drafts: POST /repost, GET /repost/{id}, GET /reposts, Telegram approval

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

The scout submits a repost draft. Pedro approves, picks the original cover, edits the caption, or rejects it on
Telegram. Nothing is published without his tap.

## Problem

There is no repost entity and no Telegram flow for it (spec §2, §3; ADR-0031).

## Scope

- Table `autopilot_reposts`, holding the draft, its status, the Telegram message id, render facts and the Graph ids.
- `POST /api/autopilot/repost`:
  - Requires an Idempotency-Key: 8–128 characters from `[A-Za-z0-9_-]`. Replaying the same key with the same body
    returns the original response. The same key with a different body answers 409 `idempotency_conflict`.
  - Validation answers 400 `invalid_field` with `field` set.
  - Other refusals: 404 `reel_not_found`, 409 `already_reposted`, 422 `too_recent`, 422 `asset_invalid`,
    422 `weekly_cap_reached`.
  - Success answers 202 with `preview_url` and `expires_at` (12 h).
- `GET /api/autopilot/repost/{id}` and `GET /api/autopilot/reposts?status=&since=&limit=`, newest first.
- The Telegram message is sent by the worker once the preview has rendered (see AE-0629). It carries the preview video,
  the cover, the caption, the original permalink with its metrics, and the reason. Buttons: Aprovar, Usar capa
  original, Editar legenda, Rejeitar.
- Owner callbacks: approve (publish time from `publish_window` and the slot scorer), approve with the original cover,
  caption edit by ForceReply, and reject. Taps after expiry or a decision do nothing.

## Non-Goals

- Publishing and rendering (AE-0629).
- Any API-key route that approves.

## Acceptance Criteria

- [ ] AC1: A valid draft is stored `pending_approval` with `expires_at = created_at + 12h` and answers 202.
- [ ] AC2: The idempotency replay and conflict behave as the spec says.
- [ ] AC3: Every validation rule in the spec table (caption length, hashtags, mentions, hook length and duration, trim
  bounds, the 3–90 s final length, reason length, publish window order) answers 400 `invalid_field` with `field`.
- [ ] AC4: Not Pedro's Reel or not a Reel → 404. Younger than 60 days → 422 `too_recent`. A live repost within 90 days
  → 409. More than 2 drafts in 7 days → 422 `weekly_cap_reached`. A bad cover → 422 `asset_invalid`.
- [ ] AC5: The draft claims its cover, so the cover cannot be used twice.
- [ ] AC6: Aprovar moves the draft to `approved` with `publish_at` inside the window, or now. Usar capa original does
  the same with `cover_choice=original`. Rejeitar moves it to `rejected`. Editar legenda replaces the caption from the
  owner's next text.
- [ ] AC7: Only the owner chat can decide, and a duplicate update does nothing.

## Gherkin Scenarios

See `backend/tests/features/autopilot_repost_drafts_ae0628.feature`.

## Affected Areas

- Backend: `modules/autopilot` (repost domain, service, store, routes, Telegram actions)
- Database: new table `autopilot_reposts`
- API: three new routes

## Dependencies

- Blocked by: AE-0627 (cover purpose)
- Related: AE-0626, AE-0629, ADR-0031

## Implementation Plan

1. Domain: draft validation, hashing, statuses, callback parsing, publish-time choice.
2. Store and migration.
3. Service and routes.
4. Telegram actions on the owner webhook.

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

Draft service with idempotent create (advisory lock + re-check), spec validation (400 invalid_field), eligibility (404/409/422), weekly cap (failed drafts excluded), single-use cover claim. Owner callbacks `ap:rp:{ok|orig|cap|no}:<id>`; caption edit via ForceReply (15 min). Publish time = best-scored slot in window via `recommend.slots_on`.

## Files Touched

- `repost_constants.py`, `domain/repost.py`, `domain/repost_rules.py`, `domain/repost_ports.py`, `domain/repost_schedule.py`, `domain/repost_copy.py`
- `application/repost_drafts.py`, `application/repost_actions.py`, `application/owner_actions.py` (mixin + caption reply hook)
- `infrastructure/repost_store.py`, `infrastructure/repost_models.py`, migration `c3d4e5f6a7b9`
- `api/repost.py`, `bootstrap_repost.py`, `bootstrap_webhook.py`, `public.py` (model registration), `bootstrap/app_factory.py`
- Tests: `test_repost_domain_ae0628.py`, `test_repost_drafts_ae0628.py`, `test_repost_actions_ae0628.py`, `test_repost_store_ae0628.py`, integration API test
- Feature: `tests/features/autopilot_repost_drafts_ae0628.feature`

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

[AE-0628.qa.md](../reports/AE-0628.qa.md), which points to the wave report [wave-reels-repost.qa.md](../reports/wave-reels-repost.qa.md). External QA (opencode) took 2 rounds and passed on `84bf6e408`; all findings are resolved. Still open in CI: `backend / Test & Coverage` and the backend mutation job.

## Decision Log

See ADR-0031.

## Blockers

None.

## Final Summary

Pending.
