# AE-0634 — Refuse Reels whose video Graph withholds; no-store on /r/; readable render errors

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0633-deploy-script-length
Kanban Card: TBD
Created: 2026-11-20
Updated: 2026-11-20

## Goal

A scout draft for a Reel that cannot be reposted is refused at once with a clear reason, and the public preview route
never leaves a stale 404 in Cloudflare.

## Problem

Field report from the scout, 2026-11-20:

- Reposts 6406650e (DUUShzhDgaE) and ba54f1f2 (DYGVx3mIYcF) were accepted with 202, then failed on the next tick with
  `source_unavailable` and an empty `error_message`. A probe from prod showed Graph returns no `media_url` for either
  Reel (Graph withholds it, usually for licensed audio). DYJJjNlo0-x returns a CDN URL, and its 15 MB download works.
  The backend cannot fetch the video at all for these Reels.
- `/r/{id}/preview.mp4` sent no `Cache-Control`, so Cloudflare cached the pre-render 404 for 4 hours, hiding the
  file from Graph at publish time.
- `preview_url` empty on `GET /repost/{id}`: by design, `null` before render and once rejected or expired. The
  scout's draft 11cb890e was rejected from Telegram at 22:01. The contract now says so.

## Scope

- `check_eligibility`: a Reel without `video_url` answers 422 `source_unavailable` before any draft is stored.
- `MESSAGE_BY_CODE`: messages for `source_unavailable` and the four render codes. A render failure saves its message
  as `error_message`.
- `/r/{id}/{file}`: `Cache-Control: no-store` on the 200 and on every 404.
- Contract doc: the new 422, `video_url: null` meaning not repostable, `preview_url` semantics, the no-store header.

## Acceptance Criteria

- [x] AC1 A draft for a Reel without `video_url` answers 422 `source_unavailable`; no row, no commit, no quota used.
- [x] AC2 A failed render stores a readable `error_message`.
- [x] AC3 Every `/r/` answer, 200 or 404, carries `Cache-Control: no-store`.
- [x] AC4 The contract doc describes the three points above and when `preview_url` is null.
- [ ] AC5 Deployed; the scout's retry of a withheld Reel gets the 422 and a downloadable Reel renders.

## Gherkin

- `backend/tests/features/autopilot_repost_drafts_ae0628.feature`: "A Reel whose video Instagram withholds is
  refused".
- `backend/tests/features/autopilot_repost_publish_ae0629.feature`: the failed-render and public-files scenarios.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/domain/repost_rules.py`
- `backend/src/rag_backend/modules/autopilot/repost_constants.py`
- `backend/src/rag_backend/modules/autopilot/application/repost_tick.py`
- `backend/src/rag_backend/modules/autopilot/api/repost_files.py`
- tests and features listed above; `docs/architecture/grokbot-reels-repost.md`

## Test Evidence

- `uv run pytest tests/unit/modules/autopilot tests/integration/test_autopilot_repost_api_ae0628.py` → 1372 passed.
- Single gates format, lint, lint-diff, strict-diff, type, imports, arch-ratchet, docstrings, dead-code,
  gherkin-refs, comments, openapi-fresh, duplication → PASS.

## Decision Log

- 2026-11-20: Refuse at POST instead of a fallback source: Graph offers no other way to the video, and the
  original Reel must not be touched.
