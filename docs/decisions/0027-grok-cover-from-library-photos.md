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

- Pedro's decision (2026-10-22): the selected photos go to the Grok Bot, image-to-image, with an
  explicit confirmation before each generation, caps of 4 per carousel and 40 per month, owner
  only. The engine on the Grok Bot side is OpenAI (ChatGPT/Codex) (Pedro, 2026-10-24); Pedro
  accepts it processing his photos.
- The Cursor automation receives the webhook body as text, so multi-MB embedded images arrive
  truncated (Grok Bot side, 2026-10-24).
- Reuse the existing bridge endpoint and callback (no new integration).
- Results are personal data: private storage, authenticated URLs only.
- A Grok Bot job takes minutes; an HTTP request cannot wait for it.

## Considered Options

1. **Send an OpenAI `images.edit`-shaped body (`operation: "images.edit"`, callback fields
   first) on the same bridge webhook whose `image` are links to a token-gated route serving the
   re-encoded photos while the job is pending; run the job in a tracked background task, log each
   generation in a new table.**
2. Embed the photos as `data:` URLs in the webhook body (built first; the automation receives
   the body as text and multi-MB bodies arrive truncated).
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
  status, error code, created/started/completed times. Pending and succeeded rows count against the
  caps; failed ones do not, up to a hard ceiling of 3x the caps (12 per carousel, 120 per month)
  that counts every attempt (decided at review; Pedro can override). The cap check and the insert
  are serialised per owner by locking the owner's user row (a Postgres race test proves exactly one
  start passes the last slot).
- The job claims its row once it has a bridge slot, right before the webhook: a row failed
  meanwhile cancels the job, so a reaped queued job never sends photos or gets billed; the stale
  reaper times started jobs from that claim.
- Any failure (webhook, bridge error, timeout, unusable image) settles the row `failed` and
  stores no asset. A run lost to a restart is failed as interrupted when next read.
- No feature flag (Pedro): an unconfigured bridge answers 503 and records nothing.

### Consequences

- Good, because nothing new is integrated: one endpoint, one callback, one job table; the edit body
  mirrors the OpenAI `images.edit` parameters the Grok Bot already speaks (Pedro, 2026-10-24).
- Good, because a photo link works only with that job's one-time callback token and only while the
  job is pending (404 otherwise, no cache, no CORS); the photo is re-encoded without metadata on
  each request and never stored as a copy.
- Bad, because the photos are processed by a third party, OpenAI (accepted by Pedro).
- Neutral, because the webhook body stays a few KB (links, not bytes); the bridge timeout and the
  failure path contain a slow or refused job.
- Neutral, because a new table reaches prod through the `create_all` bootstrap (no one-shot).

## More Information

- Follow-up (AE-0551, Pedro 2026-10-25): a generation may tick no photo. It is then a text-only
  bridge job (contract §2.5, the §2.1 body) under the same confirmation, caps and ceilings, and no
  personal photo leaves the app. The panel also uploads a new library photo from the device.
- Ticket: AE-0508. Related: ADR-0022 (image bridge), ADR-0024 (GrokBot cover asset).
