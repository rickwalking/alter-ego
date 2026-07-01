# AE-0298 — expose custom_visual_details image-guidance input in create carousel brief step

Status: In Development
Tier: T2
Priority: Medium
Type: Feature
Area: frontend
Owner: Unassigned
Branch: TBD
Created: 2026-07-01
Updated: 2026-07-01

## Goal

The Create Carousel wizard's "Topic & Brief" step offers an optional free-text input for
image-creation guidance, sending it to the backend `custom_visual_details` field that is already
fully wired end-to-end.

## Problem

The backend accepts extra guidance to steer image generation, but the frontend never renders an
input for it — so users can't supply it.

Backend (already landed — AE-0263 code shipped even though that ticket is still `Intake`):
- Request model `custom_visual_details: str | None = Field(None, max_length=500)` —
  `backend/src/rag_backend/api/schemas/carousel.py:38` (in `CarouselProjectCreate`).
- Threaded into the domain entity at `carousels/crud.py:104` and persisted
  (`infrastructure/database/models/carousel.py:96`, Text, nullable).
- Folded into **every** slide's image prompt via `_compose_scene()` as
  `"Visual direction: {details}"` (`application/services/carousel/image_prompt_package.py:57,84`),
  applied before the brand-lock wrap; empty details leave the scene byte-identical. Also busts
  per-prompt image reuse so revisions regenerate (AE-0261).
- **Note:** `CarouselProjectResponse` (`api/schemas/carousel.py:108-147`) does NOT echo the field
  back — so even once sent, it can't currently be read back.

Frontend (input absent — 0 matches for `custom_visual_details` / `customVisualDetails` /
"backdrop"/"visual direction" in `frontend/src`):
- Payload builder `frontend/src/app/dashboard/create/helpers.ts:18-35` sends only `topic`,
  `audience`, `niche`, `theme`, `image_model`, `image_style`, `strategy`.
- Zod request schema `frontend/src/schemas/carousel.ts:136-165` (`carouselCreateRequestSchema`) has
  no such field.
- Form state `frontend/src/app/dashboard/create/types.ts:3-10`; input UI
  `frontend/src/app/dashboard/create/workspace/create-topic-section.tsx:23-50` renders only
  Topic / Target Audience / Brief(Niche).

## Scope

- Add `custom_visual_details: z.string().max(500).nullable().optional()` to
  `carouselCreateRequestSchema` (`frontend/src/schemas/carousel.ts`, before the `.refine`).
- Add the field to `CreateCarouselFormState` + `INITIAL_CREATE_FORM_STATE`
  (`create/types.ts`) and include it in the payload builder (`create/helpers.ts`) as
  `custom_visual_details: form.customVisualDetails?.trim() || null`.
- Add a multiline `LabeledField` (maxLength 500, optional) in `create-topic-section.tsx` after the
  niche field, with a helper hint explaining it steers image scene/backdrop but not brand style.
- Add i18n label/placeholder/hint in `en.json` + `pt.json` under `create.form`.
- (Optional, recommended) Echo the field back: add `custom_visual_details` to backend
  `CarouselProjectResponse` and the frontend `carouselProjectResponseSchema` so the value survives
  a reload / can be shown in the read-only Brief step. If included, keep it a strictly additive,
  optional response field.

## Non-Goals

- No change to the image brand-lock (style/palette/no-text stay locked) — this only exposes the
  existing scene-guidance field.
- Not the strategy-directive split or image-phase revision-feedback threading (those belong to
  AE-0263 / AE-0261).
- No new wizard step; reuse the existing "Topic & Brief" section.

## Acceptance Criteria

- [ ] The create wizard renders an optional, multiline "image guidance / visual details" input
      (≤500 chars) in the Topic & Brief step, in both `en` and `pt`.
- [ ] Submitting the form sends `custom_visual_details` in the `POST /carousels` payload when
      filled, and `null`/omitted when blank.
- [ ] The Zod request schema validates the field (max 500, optional) and rejects >500 chars in the
      UI before submit.
- [ ] A generated carousel's slide image prompts contain the supplied guidance (verified via the
      backend prompt package), confirming the end-to-end wiring.
- [ ] (If response echo included) the field round-trips through `CarouselProjectResponse` and the
      frontend schema without breaking existing consumers.

## Gherkin Scenarios

```gherkin
Feature: Provide image guidance when creating a carousel

  Scenario: Guidance is sent to the backend
    Given the admin fills the "image guidance" field in the Topic & Brief step
    When they submit the create carousel form
    Then the POST /carousels payload includes custom_visual_details with that text

  Scenario: Blank guidance sends null
    Given the admin leaves the image guidance field empty
    When they submit the create carousel form
    Then custom_visual_details is null or omitted in the payload

  Scenario: Over-length guidance is rejected in the UI
    Given the admin types more than 500 characters into the image guidance field
    When they attempt to submit
    Then the form shows a validation error and does not submit
```

## Affected Areas

- [ ] Backend (only if response-echo option is taken: `CarouselProjectResponse`)
- [x] Frontend
- [x] Tests
- [ ] Prompts/LLM (verification only — wiring already exists)

Files:
- `frontend/src/schemas/carousel.ts`
- `frontend/src/app/dashboard/create/types.ts`
- `frontend/src/app/dashboard/create/helpers.ts`
- `frontend/src/app/dashboard/create/workspace/create-topic-section.tsx`
- `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt.json`
- (optional) `backend/src/rag_backend/api/schemas/carousel.py`

## Dependencies

- Related: AE-0263 (backend backdrop/custom-visual-details — code already landed; this is its
  frontend counterpart), AE-0261 (image-phase revision feedback).

## Decision Log

### 2026-07-01 — architect + external review (GLM 5.2)

Plan `.agent/reports/AE-0298.arch-plan.md`; review `.agent/reports/AE-0295-0299.skeptical-review.md`
(converged, no blockers).
- Backend `custom_visual_details` fully landed (accept→persist→`_compose_scene`); cap 500 matches UI.
- **Include the response echo now** (add field to `CarouselProjectResponse` + FE schema) — else the
  value vanishes on reload. Hence area effectively FE + tiny backend.
- **Test gate is deterministic:** FE payload transport + backend unit that `_compose_scene` includes
  the guidance in a delimited `Visual direction:` clause **after** the brand lock. **No full
  generation run** in tests (non-deterministic/expensive/gameable).
- **Prompt-safety honestly bounded:** the structural test proves *positioning only*, NOT
  injection-immunity; brand-bypass/cost-amplification are documented residuals (optional deny-list
  regex as a low-cost mitigation).

## Progress Log

### 2026-07-01

Ticket created from production troubleshooting session. Backend field confirmed fully wired;
scope is frontend exposure (+ optional response echo).

### 2026-07-01 — development (wave AE-0295..0299)

- Zod: `custom_visual_details` (max 500, nullable, optional) added to
  `carouselCreateRequestSchema`; response echo added to
  `carouselProjectResponseSchema` (additive optional).
- Form: `customVisualDetails` in `CreateCarouselFormState` + initial state;
  payload builder sends trimmed text or `null`.
- UI: optional multiline `LabeledField` (maxLength 500) after the niche field
  in the Topic & Brief step; label/placeholder/hint i18n'd (en+pt,
  `create.form.imageGuidance*`) with the hint stating brand style/palette
  stay locked.
- Backend: `custom_visual_details` echoed in `CarouselProjectResponse`
  (round-trip test); structural positioning test added —
  `Visual direction:` clause lands AFTER the locked `STRICT:` directives and
  the `Scene:` trailer (positioning only; injection-immunity NOT claimed —
  residual risk documented in the arch plan).

## Files Touched

- `frontend/src/schemas/carousel.ts`
- `frontend/src/app/dashboard/create/{types,helpers}.ts` (+ `helpers.test.ts`)
- `frontend/src/app/dashboard/create/workspace/create-topic-section.tsx` (+ test)
- `frontend/src/i18n/locales/{en,pt}.json`
- `frontend/tests/features/create-image-guidance.feature`
- `backend/src/rag_backend/api/schemas/carousel.py`
- `backend/tests/unit/api/test_carousel_response_echo.py` (new)
- `backend/tests/unit/application/test_image_prompt_package.py` (positioning test)

## Test Evidence

- Frontend: `npx vitest run src/app/dashboard/create` — **60 passed**
  (trimmed payload / null-when-blank / >500 schema reject / textarea cap /
  onChange patch, plus existing create-suite regression).
- Backend: `test_image_prompt_package.py` — **7 passed** (incl. new
  lock→scene→direction ordering); `test_carousel_response_echo.py` — 2 passed.
- `npm run typecheck` clean.

## QA Report

Pending.

## Blockers

None.
