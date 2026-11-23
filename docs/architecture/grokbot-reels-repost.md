# GrokBot Reels repost API (contract)

How GrokBot Scout reposts one of Pedro's past Reels. The scout picks the Reel, writes a hook and caption, and uploads a
cover. The backend renders the video, asks Pedro on Telegram, and publishes only after he approves. Decision:
[ADR-0031](../decisions/0031-owner-approved-reels-repost.md). Tickets: AE-0626 (list), AE-0627 (cover), AE-0628 (drafts
and approval), AE-0629 (render and publish).

All routes follow the autopilot conventions:

- Base URL `https://marinssolutions.com`.
- Header `X-Api-Key`.
- One shared budget of 10 requests per minute across `/api/autopilot/*`.
- Timestamps are ISO 8601 UTC.

Errors on the routes below are `{"error": {"code", "message", "field"}}`, and that includes the 429 `rate_limited`.
`POST /assets` keeps its existing `{"detail": "<code>"}` shape.

## Scout flow (twice a week)

1. `GET /api/autopilot/reels?min_age_days=60&sort=views_desc`. Pick a Reel above `baseline.median_views` and
   `baseline.median_shares_per_100_views`. Skip it if `last_repost` is set.
2. Download the video with `GET /api/autopilot/reels/{media_id}/video`, or with `video_url` before
   `video_url_expires_at`. Write the hook, the caption and an optional trim.
3. Generate a 1080×1920 cover and upload it with `POST /api/autopilot/assets`, setting `kind=ai_image` and
   `purpose=reel_cover`.
4. `POST /api/autopilot/repost` with an `Idempotency-Key`.
5. Report in chat. Pedro approves on Telegram. Poll `GET /api/autopilot/repost/{id}` to see the outcome.

## 1. `GET /api/autopilot/reels`

| Param | Default | Rules |
|-------|---------|-------|
| `min_age_days` | 60 | 0–3650, at most `max_age_days` |
| `max_age_days` | 730 | 1–3650 |
| `limit` | 50 | 1–100 |
| `cursor` | – | the opaque `next_cursor` of the previous page |
| `sort` | `views_desc` | `views_desc`, `shares_rate_desc`, `timestamp_desc` |
| `exclude_reposted_days` | 90 | 0–3650. Hides Reels with a live repost (pending, approved, processing or published) created in the window. `0` hides none of them. |

Any other parameter, or a bad value, answers 400 `invalid_field` with `field` set.

The response matches the spec, with these notes:

- A metric Graph does not return is `null`. A rate is `null` when any of its inputs is missing.
- `stale: true` means the insight snapshot is older than 6 h and was not refreshed in this request. Each request
  re-reads at most 30 snapshots, missing ones first, so repeated calls converge.
- `avg_watch_ratio` is `avg_watch_time_ms / 1000 / duration_s`. `duration_s` is probed once with ffprobe and cached;
  it is `null` until the probe has run. Each request probes at most 15 Reels, so a first page of 20 has some nulls
  and repeated calls fill them in. A Reel whose video URL Graph withholds (for example licensed audio) stays `null`.
- `collaborators` is read once from Graph's `/{media-id}/collaborators` and cached. The account's Instagram API
  answers that edge with "nonexisting field", so the list is always empty today. Send `collaborators` explicitly on
  a repost draft when the original was a collab.
- `follows` comes back `null` for Reels: Graph does not report it for that media type.
- `video_url_expires_at` is read from the CDN URL's `oe` parameter, and is `null` when the URL has none.
- `baseline` holds the medians over every Reel in the age window, before reposted ones are hidden.
- A Reel that is itself a published repost is never listed.
- Graph lists only media the account owns. A collab Reel where Pedro is only a collaborator does not appear.
- Without an Instagram account the route answers 503 `instagram_not_configured`. When Graph is down it answers 503
  `instagram_unavailable`.

### 1b. `GET /api/autopilot/reels/{media_id}/video`

Streams the MP4 (`video/mp4`). A feed post, a foreign id or an unknown id answers 404 `reel_not_found`; a Graph answer whose `owner` is neither the configured account id nor the id Graph reports for that account counts as foreign. When the CDN
fails the route answers 503 `instagram_unavailable`.

## `POST /api/autopilot/assets` with `purpose`

`purpose` is `carousel_cover` (the default, unchanged) or `reel_cover`. A Reel cover must have `kind=ai_image` and be
9:16 within 1 %, at least 1080×1920. It is scaled to exactly 1080×1920 and never cropped. Refusals are all 422:

| Code | When |
|------|------|
| `asset_ratio_invalid` | The image is not 9:16 |
| `asset_too_small` | The image is under 1080×1920 |
| `asset_kind_invalid` | `kind` is not `ai_image` |
| `asset_purpose_invalid` | `purpose` is unknown |

The body of the 201 answer now includes `purpose`. A Reel cover expires after 6 h and can be used once, by one draft.
A carousel topic cannot use a Reel cover, and a draft cannot use a carousel cover.

## 2. `POST /api/autopilot/repost`

The body follows the spec. The `Idempotency-Key` header must be 8–128 characters from `[A-Za-z0-9_-]`. Sending the
same key with the same body returns the original 202. The same key with a different body answers 409
`idempotency_conflict`.

| Field | Rules (400 `invalid_field`, `field` set) |
|-------|------------------------------------------|
| `media_id` | digits |
| `caption` | 1–2200 characters, at most 30 hashtags and 20 @mentions |
| `hook_text` | at most 90 characters. A blank hook means no hook |
| `hook_duration_s` | more than 0 and at most 4 (default 2.5) |
| `trim_start_s` / `trim_end_s` | start ≥ 0, end > start, final video 3–90 s when the duration is known |
| `cover.asset_id` | a UUID |
| `collaborators` | at most 3 usernames (the Graph limit), without `@`. Defaults to the original Reel's |
| `reason` | 10–600 characters |
| `publish_window` | both bounds carry a timezone; `latest` is after `earliest` and in the future |
| `override_weekly_cap` | boolean, default `false`. See the weekly cap below |
| `source_asset_id` | a UUID from `POST /api/autopilot/assets/video`. See the source video below |

The other refusals are listed in the spec's error table. Three codes are added: 503 `instagram_not_configured`, 503
`instagram_unavailable`, and 422 `source_unavailable` for a Reel whose video Graph withholds (no `media_url`, usually
licensed audio): such a Reel cannot be reposted, and it shows `video_url: null` in `GET /reels`, so skip it there.
Failed drafts do not count toward the weekly cap.

**Weekly cap.** At most two drafts a week count by default (pending, approved, processing, published, rejected or
expired, created in the last 7 days). When Pedro explicitly asks for an extra repost, the scout sends
`override_weekly_cap: true` and the cap is skipped for that draft. Every other rule still applies, and the draft still
waits for Pedro's approval on Telegram. The `created` log line records `cap_override`. The flag is part of the request
hash only when it is `true`, so the hash of a body without it is unchanged.

**Source video.** Graph only shares a low-quality copy of an old Reel (often 360p). When Pedro has the original take,
the scout uploads it first and names it in the draft:

1. `POST /api/autopilot/assets/video` (API key, multipart, one `file` part, at most 200 MB). The file must be an H.264
   portrait video (height greater than width, at least 720 px wide) of 3–180 s. The answer is 201
   `{"asset_id", "kind": "video", "width", "height", "duration_s", "size_bytes"}`. Refusals are `{"detail": "<code>"}`:
   400 `source_file_missing`, 413 `source_too_large`, 422 `source_not_video`, `source_codec_unsupported`,
   `source_not_portrait` or `source_duration_invalid`. nginx allows a 210 MB body on this route only.
2. `POST /api/autopilot/repost` with `source_asset_id`. The upload must exist, be under 24 h old and unused by any other
   draft, else 422 `source_asset_invalid`. The final-length check uses the upload's duration, and a Reel whose Graph
   video is withheld can be reposted this way. The trim and hook apply to the upload. `source_asset_id` is part of
   the request hash.

The worker renders the preview from the upload instead of the Graph video, then deletes the upload. A draft whose
upload is gone fails with `source_unavailable`. Uploads no draft used within 24 h are deleted on the next upload.

The 202 body matches the spec. `preview_url` points to `/r/{id}/preview.mp4`, which answers 404 until the preview is
rendered. Every `/r/` answer, 200 or 404, carries `Cache-Control: no-store`, so a CDN never keeps an early 404.

## 3. `GET /api/autopilot/repost/{id}` and `GET /api/autopilot/reposts`

The fields are the spec's, plus `permalink`, `publish_at`, `preview_url` and `expires_at`. `preview_url` is `null`
until the preview is rendered and again once the draft is rejected or expired, when its files are no longer served. A
failed draft carries `error_code` and a readable `error_message`. `cover_used`
is `grok` or `original`, and stays `null` until Pedro approves. `GET /reposts` accepts a repeatable `status`, `since`
(ISO 8601 with a timezone) and `limit` (1–100, default 20). Results are newest first.

## Lifecycle

```
pending_approval ──render ok──▶ (Telegram prompt) ──Aprovar / Usar capa original──▶ approved
       │                                   │                                      │ publish_at
       │ render failed → failed            ├─ Rejeitar → rejected                  ▼
       │                                   └─ 12 h → expired                  processing ── FINISHED ──▶ published
                                                                                   └─ ERROR / 30 min / Graph error → failed
```

- **Rendering.** The backend worker loop renders at most one draft per tick, in an ffmpeg subprocess. One pass trims,
  scales and pads to 1080×1920, sets 30 fps, encodes H.264 at up to 6 Mbps with AAC, burns in the hook for
  `hook_duration_s` and applies `+faststart`. The output must be under 100 MB and last 3–90 s. A failure ends the draft
  `failed` with `render_failed`, `render_unavailable`, `render_too_large`, `render_duration_invalid` or
  `source_unavailable`, and Pedro gets no message.
- **Telegram.** Pedro receives the new cover, the preview video (or its link when it is over 49 MB), then one prompt:
  the original permalink and metrics, the hook, the reason, the window and the caption. The prompt has four buttons:
  *Aprovar*, *Usar capa original*, *Editar legenda* and *Rejeitar*.
  - *Usar capa original* approves with the original Reel's thumbnail as the cover.
  - *Editar legenda* asks for the new caption. Pedro's next message, within 15 minutes, replaces it after the same
    caption rules. The draft stays pending and the prompt is refreshed.
- **Publish time.** On approval the publish time is the best-scored slot inside `publish_window`, using audience
  online hours and past engagement. With no window, or no slot left in it, the Reel goes out on the next tick.
- **Graph.** The worker calls `POST /{ig-user-id}/media` with `media_type=REELS`, `video_url` (the preview),
  `caption`, `cover_url` (`cover.jpg` or `original_cover.jpg`), `share_to_feed` and `collaborators`. It then polls
  `status_code` and calls `media_publish`. The original Reel is never edited or deleted.
- **Files.** `/r/{id}/preview.mp4`, `/r/{id}/cover.jpg` and `/r/{id}/original_cover.jpg` are served without a key so
  that Graph and Telegram can fetch them. They are served only while the repost is not rejected or expired.
