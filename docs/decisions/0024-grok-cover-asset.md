---
status: proposed
date: 2026-10-17
decision-makers: Pedro Marins
consulted: Claude (AE-0418), GrokBot scout cover contract (2026-10-17)
informed: delivery team
---

# ADR-0024: GrokBot cover asset for slide 1 (owner chooses per post)

## Context and Problem Statement

Slide 1 is the owner's photo on POV decks (ADR-0021, ADR-0023) and a generated hero image on
Radar IA (ADR-0020). For news topics the scout often has something better: an image it
generated for that exact topic, or a screenshot of the post or product the news is about. There
is no way to hand an image over, no rule for which images are acceptable, and no way for the
owner to pick it.

How does GrokBot deliver a slide-1 cover, and how does the owner use it without ever losing the
current default?

## Decision Drivers

- The owner decides every time; the default slide 1 never changes by itself.
- Works for every mode (`news_analysis`, `pov`, `pov_news`) with no new pipeline.
- Uploaded bytes are untrusted: check the real format, bound the size, strip metadata.
- A screenshot must come from one of the topic's own sources (no unrelated imagery).
- Existing `POST /topics` clients keep working; the GrokBot contract is fixed
  (`docs/architecture/grokbot-cover-asset.md`).

## Considered Options

1. **An image URL on the topic** that the backend downloads.
2. **Base64 bytes inside the topic JSON.**
3. **A separate upload (`POST /api/autopilot/assets`) returning an `asset_id`, named on the
   topic as `cover.asset_id`, stored as a creator asset with role `cover`.**

## Decision Outcome

Chosen: **Option 3**.

- Upload: API key and its own rate limit (30/minute per IP, outside the shared 10/minute
  autopilot budget so uploads never starve `/topics`), behind an nginx location that accepts
  6 MB bodies (nginx's 1 MB default would 413 a normal cover); one PNG/JPEG `file` ≤ 5 MB, `kind`
  (`ai_image` | `screenshot`), `source_url` for screenshots. Magic bytes decide the format; an
  `ai_image` is centre-cropped to 4:5 and must be ≥ 1080×1350 (then scaled to the slide size),
  a screenshot keeps its aspect and needs ≥ 600 px of width; 4096 px a side and 16 MP max.
  Re-encoded to WebP (metadata dropped) and stored as `carousel_creator_assets` with role
  `cover`, hidden from the owner's photo library. `autopilot_cover_assets` keeps kind, source
  and the topic that used it.
- Topic rule (per topic, last in the rule order): the asset exists, is younger than 6 h, is
  unused, and a screenshot's source is in the topic's `sources` (`cover_asset_unknown`,
  `cover_asset_expired`, `cover_asset_used`, `cover_source_invalid`, `field: "cover.asset_id"`).
  The claim is a compare-and-set checked at store time: a cover lost to a concurrent batch or the
  sweep after the read rejects the topic (`cover_asset_used` / `cover_asset_unknown`) and the
  topic row is removed.
- Owner choice on Telegram: the thesis message (POV modes) and every review message show the
  cover and a toggle (`ap:cv:<run>` / `ap:cvoff:<run>`), owner-only and idempotent. At the
  thesis the choice is stored on the run and the carousel is created with it; at the review the
  tap queues an `owner_cover` rework that stages the file, stores `carousel_projects.slide_cover`
  under the lock-version CAS and re-renders through the AE-0313 republish path. A re-render that
  reports errors is `render_failed`: the run is escalated (`cover_render_failed`) and the owner
  is told, never shown a "switched" review.
- Render: an `ai_image` replaces the slide-1 image full-bleed (POV hook photo / Radar IA intro
  artwork); a screenshot uses the new `cover_card` layout (title above a rounded, shadowed card
  and the credit `@handle · X` or the domain). A missing staged file raises
  `HookPhotoError(slide_cover_unreadable)`.
- Unused covers older than 6 h are deleted by the Telegram notify tick. Identical bytes reuse one
  creator asset, so the sweep deletes the image only when no other cover row and no project
  (`hook_asset_id`, `slide_cover`) still references it.

### Consequences

- Good, because nothing changes unless the owner taps; the default slide 1 is untouched.
- Good, because the backend never fetches a URL (no SSRF surface) and validates real bytes.
- Good, because switching after content exists reuses the "Fix issues" machinery (rework
  marker, CAS, republish, fresh review) instead of a new path.
- Bad, because a POV run keeps needing the owner's photo even when the cover is chosen (it is
  the fallback for "Usar minha foto").
- Bad, because the dashboard's slide-1 photo picker does not show the Grok cover (Telegram is
  the only place to choose it; AE-0418 Decision Log D9).
- Neutral, because the scout is responsible for the rights of what it sends (contract §6).

## More Information

- Contract: [`docs/architecture/grokbot-cover-asset.md`](../architecture/grokbot-cover-asset.md).
- Ticket: AE-0418. Related: ADR-0020 (autopilot), ADR-0021 (POV mode), ADR-0023 (`pov_news`).
