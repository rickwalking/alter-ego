# AE-0629 — Repost worker: render preview (ffmpeg), Telegram notice, Graph Reels publish, expiry

Status: In Development
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

A repost draft gets a rendered preview, which is the exact file that will be published, and reaches Pedro on Telegram.
Once he approves, it is published as a new Reel at the chosen time.

## Problem

The backend has no video pipeline. The prod image has no ffmpeg (spec "Publishing notes"; ADR-0031).

## Scope

- A worker tick, in the generation worker's autopilot sweep:
  1. Render pending drafts that have no preview. Fetch a fresh `media_url`, then run ffmpeg: trim, scale and pad to
     1080×1920, 30 fps, H.264/AAC, the hook burnt in, under 100 MB. Write `cover.jpg` and `original_cover.jpg`. Then
     send the Telegram notice.
  2. Expire pending drafts past `expires_at`, and edit their Telegram message.
  3. Publish approved drafts whose `publish_at` has passed: `approved → processing`, create the REELS container, poll
     `status_code` on later ticks, `media_publish`, read the permalink → `published`. Errors → `failed`.
- Public, keyless file routes: `/r/{id}/preview.mp4`, `/r/{id}/cover.jpg` and `/r/{id}/original_cover.jpg`, through an
  nginx location to the backend.
- Dockerfile: `ffmpeg` and `fonts-dejavu-core`.

## Non-Goals

- Editing or deleting the original Reel.
- Retrying a failed publish automatically (the scout can submit a new draft).

## Acceptance Criteria

- [ ] AC1: The ffmpeg command applies the trim, the 1080×1920 30 fps H.264/AAC output, the hook for `hook_duration_s`,
  and a bitrate cap.
- [ ] AC2: A render failure, or a file of 100 MB or more, ends the draft `failed` with `render_failed`, and no Telegram
  message is sent.
- [ ] AC3: After a successful render the owner receives the video with the four buttons, and `telegram_message_id` is
  stored.
- [ ] AC4: An unanswered draft becomes `expired` after 12 h.
- [ ] AC5: An approved draft is published only once `publish_at` has passed, with the right cover URL (Grok or
  original), collaborators and `share_to_feed`. It ends `published` with `new_media_id` and `new_permalink`.
- [ ] AC6: A Graph error ends the repost `failed` with `error_code` and `error_message`. A container still not finished
  after 30 min fails with `container_timeout`.
- [ ] AC7: The file routes serve only existing files of a live repost, and answer 404 otherwise.

## Gherkin Scenarios

See `backend/tests/features/autopilot_repost_publish_ae0629.feature`.

## Affected Areas

- Backend: repost worker, Graph gateway, render adapter, public file route
- Deployment: Dockerfile (ffmpeg), nginx `/r/` location
- Docs: the architecture contract

## Dependencies

- Blocked by: AE-0628
- Related: ADR-0031

## Implementation Plan

1. Render command builder (pure) plus a subprocess adapter.
2. Graph Reels gateway.
3. Tick service plus worker wiring.
4. Public file route, nginx and the Dockerfile.

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

Worker step runs in the backend workflow-worker loop (same loop as the boost tick), one render per tick. Found while smoke-testing a real render: drawtext expanded `%` in the hook and drew a missing-glyph box at each line break; fixed with `expansion=none` and one drawtext per line. Verified frames: hook visible at t=1 s, gone at t=3 s.

## Files Touched

- `domain/repost_render.py`, `infrastructure/repost_video.py`, `infrastructure/repost_studio.py`
- `application/repost_tick.py`, `application/repost_tick_ports.py`, `infrastructure/repost_graph.py`, `infrastructure/repost_notifier.py`
- `api/repost_files.py` (`/r/{id}/{file}`), `bootstrap/autopilot_worker_factory.py` (`RepostRunAdapter`), `application/workers/workflow_workers.py`
- `backend/Dockerfile` (ffmpeg, fonts-dejavu-core), `nginx/nginx.conf`, `nginx/nginx.conf.ssl` (`/r/`)
- Tests: `test_repost_tick_ae0629.py`, `test_repost_render_ae0629.py` (incl. a real ffmpeg render when available), `test_repost_graph_ae0629.py`, `test_repost_wiring_ae0629.py`
- Feature: `tests/features/autopilot_repost_publish_ae0629.feature`
- Docs: `docs/architecture/grokbot-reels-repost.md`, ADR-0031

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

[AE-0629.qa.md](../reports/AE-0629.qa.md), which points to the wave report [wave-reels-repost.qa.md](../reports/wave-reels-repost.qa.md). External QA (opencode) took 2 rounds and passed on `84bf6e408`; all findings are resolved. Still open in CI: `backend / Test & Coverage` and the backend mutation job.

## Decision Log

See ADR-0031.

## Blockers

None.

## Final Summary

Pending.
