# AE-0641 — The scout can supply a repost's source video

Status: In Development
Tier: T2
Priority: High
Type: Feature
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: feat/ae-0641-repost-source-video
Kanban Card: TBD
Created: 2026-11-23
Updated: 2026-11-23

## Goal

A repost can render from the owner's original high-quality take instead of the low-quality copy Graph shares.

## Problem

2026-11-23: GrokBot had the original 1080×1920, 30 fps, 14 Mbps take of a Reel. Graph's `media_url` for the same Reel
is 360p at 0.3 Mbps. The repost flow could only render from Graph's copy, so the extra repost (draft 80181042) would
publish in 360p.

## Scope

- `POST /api/autopilot/assets/video`: API key, multipart `file` up to 200 MB, streamed to
  `output/reposts/sources/`. ffprobe keeps only an H.264 portrait video (at least 720 px wide) of 3–180 s. The answer
  is 201 with `asset_id`, `kind`, `width`, `height`, `duration_s` and `size_bytes`.
- New table `autopilot_repost_sources` (Alembic `d4e5f6a7b8c0`; prod creates it at startup).
- `POST /api/autopilot/repost` accepts `source_asset_id`. The upload must be fresh (under 24 h) and unused, else 422
  `source_asset_invalid`. It is claimed by the draft, the final length uses its duration, it makes a Reel without a
  Graph video repostable, and it enters the request hash only when set.
- The worker renders from the upload and then deletes it. A missing upload fails the render with
  `source_unavailable`.
- Uploads no draft used within 24 h are swept on the next upload.
- nginx: `location = /api/autopilot/assets/video` with `client_max_body_size 210m` and request buffering off.
- `docs/architecture/grokbot-reels-repost.md` documents the route and field.

## Non-Goals

- Owner approval on Telegram is unchanged: nothing publishes without it.
- No change to the render settings, the cap, or the cover upload.

## Acceptance Criteria

- [ ] A valid upload answers 201 and is stored; an unusable one is refused with its code and leaves no file.
- [ ] A draft with a fresh upload is accepted and claims it; an unknown, used or expired upload is 422
      `source_asset_invalid`.
- [ ] The worker renders from the upload, not the Graph video, and deletes the upload afterwards.
- [ ] A body without `source_asset_id` hashes exactly as before.
- [ ] Both nginx configs let a 200 MB upload through.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests
- [x] Docs
- [x] Infra (nginx)

## Dependencies

AE-0640 (weekly cap override), merged.

## Progress Log

### 2026-11-23

Ticket created from GrokBot's request for a source video upload.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/repost_source_constants.py` (new)
- `backend/src/rag_backend/modules/autopilot/domain/repost_source.py` (new)
- `backend/src/rag_backend/modules/autopilot/domain/repost_source_ports.py` (new)
- `backend/src/rag_backend/modules/autopilot/application/repost_source_upload.py` (new)
- `backend/src/rag_backend/modules/autopilot/infrastructure/repost_source_files.py` (new)
- `backend/src/rag_backend/modules/autopilot/infrastructure/repost_source_models.py` (new)
- `backend/src/rag_backend/modules/autopilot/infrastructure/repost_source_store.py` (new)
- `backend/src/rag_backend/modules/autopilot/api/repost_source.py` (new)
- `backend/alembic/versions/d4e5f6a7b8c0_autopilot_repost_sources.py` (new)
- `backend/src/rag_backend/modules/autopilot/api/repost_schemas.py`, `api/repost_mapping.py`, `domain/repost.py`,
  `domain/repost_rules.py`, `application/repost_drafts.py`, `application/repost_tick.py`,
  `infrastructure/repost_studio.py`, `bootstrap_repost.py`, `public.py`, `repost_constants.py`
- `backend/src/rag_backend/bootstrap/app_factory.py`
- `nginx/nginx.conf`, `nginx/nginx.conf.ssl`
- `docs/architecture/grokbot-reels-repost.md`, `docs/architecture/openapi.json`
- Tests: `test_repost_source_upload_ae0641.py`, `test_repost_source_drafts_ae0641.py`, `repost_source_fakes.py`,
  `test_nginx_source_video_ae0641.py`, `test_autopilot_repost_source_api_ae0641.py`,
  `autopilot_repost_source_video_ae0641.feature`

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
