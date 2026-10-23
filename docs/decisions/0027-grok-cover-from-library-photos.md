---
status: proposed
date: 2026-10-23
decision-makers: Pedro Marins
consulted: Claude (AE-0508)
informed: delivery team
---

# ADR-0027: Generate slide-1 covers from the owner's library photos through the image bridge

## Context and Problem Statement

The publish-step cover picker (AE-0445) lets the owner switch slide 1 between their library
photos and the autopilot's GrokBot cover offer (ADR-0024). There is no way to ask Grok for a new
cover of the owner from their own photos. The image bridge (ADR-0022) already sends image jobs
to the Grok Bot and receives the image through a token-checked callback, but its body carries a
text prompt only.

How does the owner get a Grok-made cover from their photos without a new provider, a public URL
to a personal photo, or uncontrolled spend?

## Decision Drivers

- Pedro's decision (2026-10-22): the selected photo's bytes go to the Grok Bot (no URL leaves the
  app), image-to-image, with an explicit confirmation before each generation, caps of 4 per
  carousel and 40 per month, owner only. Pedro accepts xAI processing his photos.
- Reuse the existing bridge endpoint and callback (no new integration).
- Results are personal data: private storage, authenticated URLs only.
- A Grok Bot job takes minutes; an HTTP request cannot wait for it.

## Considered Options

1. **Extend the bridge body with optional `task` + `reference_images` (base64 PNG), run the job
   in a tracked background task, log each generation in a new table.**
2. Upload the photos to a signed URL the Grok Bot downloads.
3. Text-only Grok scenes composited with the existing photo in the template.

## Decision Outcome

Chosen: **option 1**. Contract: [GrokBot Image Bridge §2.4](../architecture/grokbot-image-bridge.md).

- `POST /api/carousels/{id}/cover-generations` (owner only, `confirmed: true`, 1–3 own photos,
  a 3–500 character direction) records a `pending` row and returns 202; a tracked asyncio task
  runs the bridge job on its own session. `GET` returns the caps in use and the generations.
- The result passes the `ai_image` cover rules and is stored as a creator asset with role
  `cover` (hidden from the photo library, served only by the authenticated image route). It
  appears in the cover options as `source: "generated"` and is picked through `PUT /cover`,
  stored as an `ai_image` `slide_cover`. Library photos stay options (the default slide 1).
- `carousel_cover_generations` is the budget log: time, carousel, owner, prompt SHA-256, photo
  count, model, cost (`GROK_COVER_COST_USD`, default 0: the Grok Bot runs on a subscription),
  status, error code. Pending and succeeded rows count against the caps; failed ones do not. The
  cap check and the insert are serialised per owner by locking the owner's user row.
- Any failure (webhook, bridge error, timeout, unusable image) settles the row `failed` and
  stores no asset. A run lost to a restart is failed as interrupted when next read.
- No feature flag (Pedro): an unconfigured bridge answers 503 and records nothing.

### Consequences

- Good, because nothing new is integrated: one endpoint, one callback, one job table.
- Good, because no URL to a personal photo exists; the bytes are re-encoded without metadata.
- Bad, because the photos are processed by a third party (accepted by Pedro).
- Bad, because a 1–5 MB webhook body is larger than a text job's; the bridge timeout and the
  failure path contain a slow or refused job.
- Neutral, because a new table reaches prod through the `create_all` bootstrap (no one-shot).

## More Information

- Ticket: AE-0508. Related: ADR-0022 (image bridge), ADR-0024 (GrokBot cover asset).
