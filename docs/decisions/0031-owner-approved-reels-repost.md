---
status: proposed
date: 2026-11-19
decision-makers: Pedro Marins
consulted: spec "Alter-ego Autopilot: Reels repost API (spec v1)"
informed: delivery team
---

# ADR-0031: Owner-approved Reels reposts

## Context and Problem Statement

GrokBot Scout should run twice a week. Each run picks a past Reel that did well, writes a new hook and caption, makes a new
cover, and asks to repost it. Nothing may be published until Pedro taps Approve on Telegram, the same rule as boosts
(ADR-0029). The backend has the pieces: the autopilot `X-Api-Key`, the Graph media walk, the insights snapshot cache
(6 h), cover uploads (ADR-0024), the Telegram owner gate, the slot scorer and the Graph container flow. It has no video
pipeline: the production image does not ship ffmpeg, and the Graph media walk keeps neither media URLs nor full captions.

## Decision Drivers

- The scout never holds a Meta token and can never publish. Only an owner callback approves.
- The preview Pedro sees on Telegram is the exact file that gets published (same hook, same trim).
- Reuse the autopilot key, the shared 10/min budget, the insights snapshots, cover assets and the Telegram webhook.
- Never edit or delete the original Reel.
- Rendering must not block an API request or the web process.

## Considered Options

1. Download, render and send to Telegram inside `POST /repost`.
2. `POST /repost` stores a draft and returns 202. The backend's workflow-worker loop (the same loop that runs the boost
   tick) renders the preview in an ffmpeg subprocess, then messages Pedro. After approval the same loop publishes through
   the Graph Reels flow.
3. Let the scout render the video and upload the finished file.

## Decision Outcome

Chosen option 2.

- **Routes** (`/api/autopilot/*`, API key, shared 10/min): `GET /reels`, `GET /reels/{media_id}/video`,
  `POST /repost` (Idempotency-Key), `GET /repost/{id}`, `GET /reposts`. The new routes answer errors as
  `{"error": {"code", "message", "field"}}`. The older autopilot routes keep `{"detail": ...}`.
- **Render first, then ask.** A new draft is `pending_approval` with no `preview_ready_at`. The worker loop renders
  at most one draft per tick, as an isolated step next to the boost tick. It fetches a fresh
  `media_url` from Graph, then runs one ffmpeg pass: trim, scale and pad to 1080×1920, 30 fps, H.264/AAC, the hook burnt
  in with `drawtext` for the first `hook_duration_s`, `-maxrate 6M`, `+faststart`. The output must stay under 100 MB.
  The same pass writes `cover.jpg` (the Grok cover) and `original_cover.jpg` (the Reel's thumbnail). Only then is the
  Telegram message sent. The 12 h approval window starts at `created_at`. A failed render ends the draft as `failed`
  (`render_failed`) and the scout receives no Telegram message.
- **Files** live under `output/reposts/{id}/`, which is the volume the web and worker containers already share. They are
  served without a key at `/r/{id}/preview.mp4`, `/r/{id}/cover.jpg` and `/r/{id}/original_cover.jpg`, so Graph and
  Telegram can fetch them. The id is a random UUID. A file is served only while its repost is not `rejected` or
  `expired`.
- **Approval.** Telegram buttons `rp:ok`, `rp:orig`, `rp:cap` and `rp:no`, each carrying the repost id. `rp:orig`
  approves and publishes with the original thumbnail as the cover. `rp:cap` asks for a new caption by ForceReply; the
  next owner text replaces the caption, and the draft stays pending. At approval the publish time is the best-scored slot
  (`domain/recommend.py`) inside `publish_window`. With no window, or no slot left in it, the Reel publishes now.
- **Publish.** At `publish_at` the worker moves `approved → processing`. It creates `POST /{ig-user-id}/media` with
  `media_type=REELS`, `video_url`, `caption`, `cover_url`, `share_to_feed` and `collaborators`, stores the container id,
  polls `status_code` on later ticks (giving up after 30 minutes), then calls `media_publish` and reads the permalink.
  A Graph error ends the repost as `failed` with Graph's code.
- **Rules.** A Reel must be at least 60 days old. There is at most one live repost per Reel in 90 days. At most 2 drafts
  are created in a rolling 7 days, and failed drafts do not count. A Reel that is itself a repost is never offered again.
- **Image.** The backend image installs `ffmpeg` and `fonts-dejavu-core`. Without ffmpeg, `GET /reels` returns
  `duration_s: null` and the render fails with `render_unavailable`.

### Consequences

- Good: Pedro approves the exact file that will go live. The scout cannot publish. No request handler does video work;
  the render is an async subprocess of the worker loop, so it never blocks the event loop.
- Good: insights reuse the existing snapshot table and its 6 h freshness rule.
- Bad: the backend image grows by about 80 MB for ffmpeg.
- Bad: Graph only lists media the account owns. A collab Reel where Pedro is only a collaborator does not appear.
- Neutral: Graph does not return a video's duration, so `GET /reels` probes it once with ffprobe (a few Reels per
  request) and caches it in `autopilot_reel_facts`.

## More Information

Contract: [`docs/architecture/grokbot-reels-repost.md`](../architecture/grokbot-reels-repost.md). Tickets AE-0626 to
AE-0629.
