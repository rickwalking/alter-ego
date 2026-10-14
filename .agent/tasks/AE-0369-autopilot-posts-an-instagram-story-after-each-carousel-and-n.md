# AE-0369 — Autopilot posts an Instagram Story after each carousel and nudges the owner to add music

Status: In Development
Tier: T1
Priority: P1
Type: Bugfix
Area: backend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0369-story-and-music
Created: 2026-10-14
Updated: 2026-10-14
Parent: AE-0348

## Goal

Every carousel the autopilot (or the owner's manual route) posts is announced by one Instagram
Story, and the owner's Telegram "published" notice says whether the Story went out and which
music to add in the app.

## Problem

A carousel post gets little reach without a Story, and the owner adds music by hand in the app
(the Graph API cannot add music to a feed post). Today the autopilot posts the carousel only,
and the notice reads `✅ posted <permalink>` with nothing to act on.

Verified constraints: Instagram Login (`graph.instagram.com`, `instagram_business_content_publish`)
supports Stories for Business and Creator accounts (`media_type=STORIES` + `image_url`, JPEG,
9:16, ≤ 8 MB, then `status_code`, then `media_publish`). Link/mention/poll stickers and
"share post to story" are not available through the API. Music on feed posts is app-only.

## Scope

- Story image `story_pt.jpg`: 1080x1920 JPEG ≤ 8 MB, rendered with Pillow from the PT slide 1
  centred on a blurred, darkened copy of itself, with the caption band `Novo post no perfil ↑`.
  Stored in the serving root (active artifact version, else the output dir).
- Public route `GET /api/carousels/{id}/story-image/pt.jpg` (`image/jpeg`), gated by
  `is_public` like `slide-images`; 404 otherwise.
- Story step after a successful publish (worker tick and manual route): idempotent per carousel
  (`instagram_stories` row), container committed before `media_publish`, transient Graph errors
  retried up to 3 attempts, failures recorded and told to the owner, never a publish failure.
- Publisher: `create_story_container`; `fields` on every Graph GET (the quota read now asks
  for `config,quota_usage`).
- Telegram published notice: `✅ Publicado: <permalink>`, `📲 Story: publicado` /
  `📲 Story falhou: <reason>`, `🎵 Adicione uma música pelo app (20s): sugestão: <style>`, the
  style from a deterministic niche / image-style map in constants.
- One additive Alembic migration (`f8a9b0c1d2e3`, table `instagram_stories`).

## Non-Goals

- Do not refactor unrelated code.
- Stickers, links, or music through the API (not supported by Meta).
- An EN Story.
- Retrying a failed Story from Telegram (the owner can post one in the app).

## Acceptance Criteria

- [x] Story render: 1080x1920 JPEG ≤ 8 MB, deterministic, cached until slide 1 changes.
- [x] Public route serves the Story of a public carousel; 404 when private, missing, or unknown.
- [x] Graph shapes (respx): `media_type=STORIES` + `image_url`, `status_code` polled with
  `fields` until `FINISHED`, `media_publish` with `creation_id`.
- [x] A double tick posts one Story; a stored Story short-circuits; a stored container is
  resumed, an expired `PUBLISHED` one is not reposted.
- [x] Transient error retried up to 3 attempts; permanent error recorded.
- [x] A Story failure leaves the run `published` and the notice says `Story falhou: <reason>`.
- [x] Notice copy with permalink, Story line, and music suggestion; music map by niche / style.
- [x] Manual route posts the Story once, behind the same idempotency.
- [x] Gherkin: `backend/tests/features/autopilot_story_and_music.feature`.
- [ ] DB gates (test, diff-cover, migrations, schema-drift) and the Python 3.11 import check,
  relayed from the x86 orchestrator.

## Repro Steps

1. Approve an autopilot carousel; the worker publishes it.
2. Before: no Story, notice `✅ posted <permalink>`.
3. After: one Story posted; notice with the post link, the Story outcome, and a music suggestion.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

AE-0364 (merged). **Migration `f8a9b0c1d2e3` must be applied by hand on prod** (prod deploys do
not run Alembic).

## Progress Log

### 2026-10-14

Ticket created from the owner brief (hotfix fast path, behaviour change → Gherkin first).
Implemented on the Pi; static backend gates run here, DB gates relayed to x86.

## Files Touched

- `backend/alembic/versions/f8a9b0c1d2e3_instagram_stories.py` (new)
- `backend/src/rag_backend/domain/constants/instagram_publish.py`
- `backend/src/rag_backend/infrastructure/external/meta_instagram_publisher.py`
- `backend/src/rag_backend/infrastructure/external/instagram_graph_payloads.py`
- `backend/src/rag_backend/api/routes/carousels/story_image.py` (new), `router.py`
- `backend/src/rag_backend/modules/publishing/application/story_image.py` (new)
- `backend/src/rag_backend/modules/publishing/infrastructure/story_image_target.py` (new)
- `backend/src/rag_backend/modules/publishing/{constants,public,__init__}.py`,
  `domain/instagram_target.py`
- `backend/src/rag_backend/modules/autopilot/story_constants.py` (new)
- `backend/src/rag_backend/modules/autopilot/domain/{story,music,published_copy}.py` (new),
  `publish.py`, `messages.py`
- `backend/src/rag_backend/modules/autopilot/application/story_step.py` (new),
  `publish_job.py`, `manual_publish.py`, `publish_steps.py`, `notifications.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/{story_gateway,story_media,story_store}.py`
  (new), `models.py`, `publish_notifier.py`, `instagram_gateway.py`
- `backend/src/rag_backend/modules/autopilot/{bootstrap,public,notify_constants,recovery_constants}.py`
- `backend/tests/features/autopilot_story_and_music.feature` (new)
- `backend/tests/unit/modules/autopilot/test_story_{step,gateway_graph,music_copy,persistence}.py` (new)
- `backend/tests/unit/modules/publishing/test_story_image.py` (new)
- `backend/tests/unit/modules/autopilot/test_telegram_messages.py`,
  `backend/tests/integration/test_autopilot_migration.py`, `backend/tests/snapshots/openapi_routes.json`
- `docs/architecture/grokbot-autopilot.md` (§5.4)

## Test Evidence

See `.agent/reports/AE-0369.dev-summary.md` (GATES_JSON line).

## QA Report

Pending.

## Blockers

None.
