# AE-0551 — Cover generation without photos; upload photos from the cover panel

Status: In Development
Tier: T2
Priority: Medium
Type: Feature
Area: Backend + Frontend
Owner: Claude Code (claude-opus-5-5)
Branch: feat/ae-0551-cover-text-only-upload
Created: 2026-10-25
Updated: 2026-10-25

## Goal

The publish step's "Gerar capa com Grok" panel works with no photo ticked: a text prompt (the AE-0509 /
AE-0547 suggestions are the tips) asks the Grok Bot for a cover from words alone. In the same panel an
"Enviar foto" button adds a new photo from the device straight into the owner's library and ticks it for
the next generation.

## Problem

Pedro, 2026-10-25: "Allow me to create images without any other background by giving tips on the word."
and "Upload images to be sent, not just select existing images."

- `POST /api/carousels/{id}/cover-generations` requires 1-3 `photo_ids` (AE-0508), and the panel renders
  nothing when the library is empty and disables "Gerar capa" until a photo is ticked.
- New photos can only be uploaded in the create wizard's "Foto do slide 1" step.

## Scope

- API: `photo_ids` takes 0-3 ids and may be absent (default `[]`). More than 3 ids, and any id that is not
  one of the caller's own library photos, are still refused (422 / `cover_generation_photo_not_allowed`).
- A generation with no photo is a text-only bridge job: exactly the contract §2.1 body (no `operation`, no
  `image`), the same bridge model, size `1024x1536`, `metadata.content_type` `carousel_cover`, through the
  same cover editor (its slots, the claim before the webhook, no OpenAI fallback). Its prompt is the new
  versioned template `cover_generation/v1/generate` (a cover scene from the owner's direction: 4:5, calm
  top third for the title, no text or logos; no reference-photo instructions). With photos the AE-0508
  `edit` template is unchanged.
- Everything else is the AE-0508 path, unchanged: confirmation, owner only, POV only, caps 4/40, attempt
  ceilings 12/120, one pending generation per carousel, 409/422/503 refusals, the `cover_generation` log
  line and row (prompt SHA-256, never the text; `photo_count` 0), the result stored as a private role
  `cover` / kind `ai_image` asset offered in the cover grid.
- Frontend panel (`CoverGeneratePanel`):
  - renders with an empty library; "Gerar capa" needs only a prompt of 3+ characters (photos optional, at
    most 3 ticked);
  - the confirmation dialog for a no-photo generation says only the description is sent (no photo
    claim); with photos it keeps the AE-0508 wording;
  - "Enviar foto" uploads through the library upload (`POST /api/carousels/creator-assets`, role `hook`:
    same validation, 5 MB / PNG, WebP, JPEG limits and metadata stripping as the wizard), composed by the
    publish page (the upload hook lives in the editorial module); on success the cover options and the
    photo library refresh and the new photo is ticked when fewer than 3 are ticked. A refused file shows
    the wizard's upload error sentence.
- Copy in pt and en.

## Non-Goals

- No change to the image-edit body, the photo links, the caps or the attempt ceilings.
- No feature flag (Pedro): live once the bridge is configured, 503 otherwise.
- No new upload endpoint and no change to its validation.

## Threat notes

- A no-photo job sends no personal photo: only the sanitised, delimited direction inside the template.
  The dialog still names OpenAI (ChatGPT) as the processor and the caps.
- An uploaded photo goes through the existing creator-asset upload (owner's library, re-encoded, metadata
  dropped); it is sent to the Grok Bot only when ticked and the generation is confirmed.
- Spend: a text-only generation counts against the same caps, attempt ceilings and rate limit.

## Acceptance Criteria

- [ ] Given the cover panel with no photo ticked, When Pedro writes a prompt (3-500 chars) or picks a
      suggestion, clicks "Gerar capa" and confirms, Then a text-only bridge job runs and the result lands
      as a role-cover asset selectable in the grid; the API accepts `photo_ids: []` (and absent) and still
      refuses more than 3 ids and foreign ids.
- [ ] Given the cover panel, When Pedro uploads a photo, Then it appears in the panel and in the photo
      library, is ticked, and the next generation sends it; an invalid file shows the same error as the
      library upload.
- [ ] Caps, attempt ceilings, 409/422/503 refusals, the no-prompt-text logging and the one-pending-per-
      carousel lock behave exactly as with photos.
- [ ] The confirmation for a no-photo generation does not claim photos are sent.

## Gherkin Scenarios

See `backend/tests/features/cover_generation_text_ae0551.feature` and
`frontend/tests/features/cover-generation-text-upload-ae0551.feature`.

## Affected Areas

- [ ] Backend (`api/schemas/carousel_cover_generation.py`, `api/routes/carousels/cover_generate.py`,
      `agents/cover_generation_prompts.py`, prompt template `cover_generation/v1/generate.yaml`)
- [ ] Frontend (`cover-generate-panel.tsx`, `cover-generate-parts.tsx`, `use-cover-generate-form.ts`,
      `cover-picker-section.tsx`, `publish-cover-picker.tsx`, types, i18n)
- [ ] API: `photo_ids` is optional with 0-3 items (OpenAPI artifact)
- Database: no change (`photo_count` 0 and `photo_ids` `[]` fit the AE-0508 columns).
- [ ] Docs: bridge contract §2.5

## Dependencies

AE-0508 (#270), AE-0509 (#273), AE-0547 (#280), all merged. The text-only body is the contract §2.1 body
the Grok Bot already answers for slide images; `metadata.content_type` `carousel_cover` is informational.
A live check of one text-only cover is done on prod after merge.

## Progress Log

### 2026-10-25

Ticket written from Pedro's asks; failing tests first.

## Files Touched

See `.agent/reports/AE-0551.dev-summary.md`.

## Test Evidence

See `.agent/reports/AE-0551.dev-summary.md`.

## QA Report

See `.agent/reports/AE-0551.qa.md`.

## Blockers

None.
