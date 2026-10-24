# AE-0508 — Generate new cover images from library photos with Grok

Status: In Development
Tier: T2
Priority: High
Type: Feature
Area: Backend + Frontend
Owner: Claude Code (claude-opus-5-5)
Branch: feat/ae-0508-grok-cover-from-photos
Created: 2026-10-23
Updated: 2026-10-23

## Goal

On the publish step of a Ponto de Vista carousel the owner picks one to three of their library photos,
writes a prompt and, after an explicit confirmation, has the Grok Bot generate a new slide-1 cover from
those photos (image-to-image). The result lands in the owner's private library with role `cover` and can
be picked like any other cover; the default slide 1 (the owner's photo) stays an option.

## Problem

Dashboard QA (DQ-C-02): there is no dashboard action to generate new cover images with Grok. The publish
step cover picker only lists library photos and the passive autopilot GrokBot offer. The image bridge
(ADR-0022) is text-prompt only.

## Scope

Pedro's decision (2026-10-22): extend the bridge to carry the selected photos' bytes (no URL leaves the
app), image-to-image with the same Grok model as the autopilot cover flow; an explicit confirmation before
each generation; caps of 4 per carousel and 40 per month; owner only. Pedro accepts OpenAI (ChatGPT, the Grok Bot's engine) processing his
photos.

- Image bridge webhook (contract §2.1) gains two optional fields, sent only for a cover generation:
  `operation: "images.edit"` and `image: ["https://…/api/v1/image-bridge/jobs/{job_id}/inputs/{n}"]`
  (OpenAI `images.edit` shape, callback fields first; the Grok Bot fetches each photo with the
  callback token while the job is pending; 1-3
  photos, re-encoded to PNG, at most 3 MB each,
  at most 1024 px a side, no metadata) on the same endpoint and callback as the text path (Pedro: the
  Grok Bot side already takes image requests through its sidecar, so no bot-side change). `model` is the
  bridge's model, `size` is `1080x1350`, `metadata.content_type` is `carousel_cover`. No OpenAI fallback
  for these jobs. Text-only jobs send exactly the old body.
- `GET /api/carousels/{id}/cover-generations` (owner only): the caps in use and the carousel's generations
  (status, error code, result asset).
- `POST /api/carousels/{id}/cover-generations` `{photo_ids: [1-3], prompt: 3-500 chars, confirmed: true}`
  (owner only, POV carousels): records a `pending` generation and returns 202; the bridge job runs in the
  background (tracked task). Refusals: 422 `cover_generation_not_confirmed`, `cover_pick_not_pov`,
  `cover_generation_photo_not_allowed`; 409 `cover_generation_in_progress`, `cover_generation_carousel_cap`,
  `cover_generation_monthly_cap`; 503 `cover_generation_unavailable` (bridge not configured); 403 for
  anyone but the owner (admins included), 404 unknown carousel.
- The background run sends the photos, validates the image with the `ai_image` cover rules (centre crop
  4:5, at least 1080x1350, WebP, metadata dropped) and stores it as a creator asset with role `cover`
  (private; served only through the authenticated library image route). Any failure (webhook, bridge
  failure, timeout, invalid image) marks the generation `failed` with a code and stores no asset. A
  generation still `pending` after the bridge timeout plus a grace period (process restart) is failed as
  `cover_generation_interrupted` when read.
- Caps: succeeded and pending generations count; failed ones do not (retry is free). 4 per carousel,
  40 per calendar month (UTC; resets at 21:00 BRT on the last day of the month) per owner. Hard attempt
  ceiling of 3x the caps (12 per carousel, 120 per month) counting every attempt, failures and timeouts
  included (409 `cover_generation_carousel_attempts` / `cover_generation_monthly_attempts`).
- A queued job claims its row once it has a bridge slot, right before the webhook; a row failed
  meanwhile cancels the job (nothing sent, nothing billed). The stale reaper times started jobs from
  that claim (`started_at`).
- Every call is logged: one row per generation (`carousel_cover_generations`: time, carousel, owner,
  prompt SHA-256, photo count, model, cost from `GROK_COVER_COST_USD` (default 0: the Grok Bot runs on a
  subscription), status, error code) and a structured log line
  `cover_generation` with the same fields (no prompt text, no image bytes).
- Cover options list the carousel's generated covers (`source: "generated"`, kind `ai_image`); picking one
  goes through `PUT /api/carousels/{id}/cover` and stores it as `slide_cover` (full-bleed, like the
  GrokBot `ai_image`). Library photos stay options, so the default slide 1 is always one tap away.
- Publish step: a "Gerar capa com Grok" panel in the cover picker: photo checkboxes, prompt, usage
  ("1 de 4 neste carrossel · 3 de 40 no mês"), "Gerar capa" → confirmation dialog (names OpenAI (ChatGPT), the photo
  count and the caps) → progress line while pending → the result appears in the grid; a failure shows
  the reason and "Tentar de novo". A reached cap disables the button and says why.

## Non-Goals

- No wizard (create) entry point; the prompt suggestions are AE-0509.
- No change to the autopilot GrokBot cover upload or the Telegram choice.
- No deletion of generated covers from the dashboard (they are hidden from the photo library like every
  role `cover` asset).
- No feature flag (Pedro): the action is live once the bridge is configured; unconfigured → 503.

## Threat notes (risk high: personal data to a third party, paid calls)

- **Personal data egress.** The owner's photos leave the app to the Grok Bot and OpenAI (ChatGPT).
  Mitigations: owner only (not admins), an explicit `confirmed: true` per generation backed by a dialog
  that names OpenAI (ChatGPT); only the photos the owner ticked are linked, re-encoded on request
  (EXIF/GPS and every metadata block dropped), capped at 1024 px and 3 MB. The links
  (`/jobs/{job_id}/inputs/{n}`) serve only with that job's one-time callback token (constant-time
  compare), only while the job is pending and before its deadline; everything else is 404 (no existence
  leak), `Cache-Control: no-store, private`, no CORS headers, no copy stored, no token in a URL or log.
  Photos never enter fixtures; tests use generated images.
- **Spend abuse.** Caps 4/carousel and 40/month enforced server-side, one pending generation per carousel,
  rate limit on the POST (5/minute per user), failures do not count. The cap check and the insert run in
  one transaction after locking the owner's user row (`SELECT ... FOR UPDATE`), so two clicks cannot both
  pass the last slot.
- **Untrusted output.** The bridge callback is already token-authenticated and size-bounded; the result is
  decoded with the pixel budget, re-encoded and stored as a private creator asset. No URL from the bot is
  ever fetched (no SSRF).
- **Exposure of results.** Generated covers are creator assets with role `cover`: served only by the
  authenticated library image route (owner or admin), hidden from the photo library and never given a
  public URL until the owner picks one and the carousel is published.
- **Prompt injection / logging.** The prompt is forwarded as the image instruction only (no LLM tool
  access). Logs carry its SHA-256, never the text, and never the webhook URL, auth value, callback token
  or image bytes.
- **IDOR.** Every photo id must be the caller's own library photo (role `hook`, file present); another
  owner's id is refused like an unknown one.

## Acceptance Criteria

- [x] Given a POV carousel's cover picker, When the owner selects 1-3 library photos, writes a prompt,
      clicks "Gerar capa" and confirms, Then a Grok job runs with progress, the photos' bytes are sent in
      the webhook (no URL), and the result lands in the private library with role `cover`.
- [x] Given results, When the owner picks one, Then `PUT /api/carousels/{id}/cover` uses it and the
      default slide 1 (library photo) is still offered.
- [x] Given the GrokBot bridge fails or times out, Then the generation shows a failure with "Tentar de
      novo" and no asset is stored.
- [x] Given 4 generations on the carousel or 40 in the month, Then the action is disabled with the reason
      and the API refuses with 409.
- [x] Every call is logged (time, carousel, prompt hash, cost).
- [x] Only the carousel owner can generate; confirmation is required.

## Gherkin Scenarios

See `backend/tests/features/cover_generation_ae0508.feature` and
`frontend/tests/features/cover-generation-ae0508.feature`.

## Affected Areas

- [x] Backend (`modules/image_bridge`, cover generation service/repository, `cover_pick.py`, new route)
- [x] Frontend (`cover-picker-section.tsx`, new generate panel + hook, i18n)
- [x] API (OpenAPI artifact: `GET/POST /api/carousels/{id}/cover-generations`)
- [x] Database: new table `carousel_cover_generations` (alembic revision; prod's `create_all` bootstrap
      creates a missing table with its indexes, so no deploy one-shot is needed)
- [x] Docs: bridge contract §2.4, ADR-0027
- [x] Tests

## Dependencies

The Cursor automation behind the bridge webhook must handle `operation: "images.edit"` (contract §2.4,
Pedro's option (a), 2026-10-24). The first live check (bridge job `7d73695e-9783-46cf-9041-de78a35470f2`,
the earlier custom `task`/`reference_images` body) got no callback. Merge blocker until Pedro updates the
automation and one new live check with a synthetic image passes.

## Progress Log

### 2026-10-23

Ticket written from Pedro's decision; failing tests first. Pedro: no Grok Bot side change, the existing
bridge endpoint (sidecar) takes the job; after the first live check Pedro chose an OpenAI
`images.edit`-shaped body (`operation`, `image` as data URLs) on the same webhook. Backend, frontend,
docs (contract §2.4, ADR-0027). Independent review round: transaction released before the bridge wait,
unexpected errors settle failed, one shared bridge editor, the budget log survives a carousel delete,
1024 px reference photos, no dead button when the list fails. The prompt field takes a children slot for
the AE-0509 suggestions. PR review: the job claims its row once it holds a bridge slot (a reaped
queued job sends nothing), Postgres race tests for the last slot, a hard attempt ceiling of 12 per
carousel / 120 per month counting failures, the result file removed when settling fails, and the
21:00 BRT reset shown in the usage line.

## Files Touched

See `.agent/reports/AE-0508.dev-summary.md`.

## Test Evidence

See `.agent/reports/AE-0508.dev-summary.md`.

## QA Report

See `.agent/reports/AE-0508.qa.md`.

## Blockers

Grok Bot sidecar does not answer image-edit jobs (live check above); outside this repo.
