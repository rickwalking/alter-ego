# AE-0509 — Prompt suggestions for a new cover photo

Status: Dev Complete
Tier: T2
Priority: Low
Type: Feature
Area: Backend + Frontend
Owner: Claude Code (claude-opus-5-5)
Branch: feat/ae-0509-cover-prompt-suggestions
Created: 2026-10-23
Updated: 2026-10-24

## Goal

Under "Foto do slide 1" the owner gets three to six prompt suggestions for a new cover photo (angle,
background, mood, palette-aware); tapping one fills an editable prompt field. The same suggestions
component is ready for the Grok cover dialog.

## Problem

Dashboard QA (DQ-C-03): `create-photo-section.tsx` has a hint and an upload only. There are no prompt
suggestions for a new photo and no endpoint for them.

## Scope

Pedro's decision (2026-10-22): a curated catalogue first; "Mais ideias" asks the LLM for topic- and
palette-tailored ideas on demand (fast queue, `LLM_MODEL_QUEUE_FAST` through the container's fast LLM
service). No personal data beyond the carousel topic.

- Frontend: `CoverPromptField` in `modules/editorial` (exported from the barrel): an editable prompt
  textarea (max 400) with `CoverPromptIdeas` under it. Six curated suggestions (frontal, three-quarter,
  low angle, desk, gesture, close-up) are filled with the selected palette's name and colours (neutral
  wording for "auto") and end with a nod to the topic (cut at 80 characters). "Mais ideias" needs a topic of
  3+ characters and replaces the list with the AI ideas; a failure keeps the curated list and shows a
  retryable error. The create page resolves the theme to a palette (`findThemePalette`) and renders the
  field inside the Slide 1 photo section (POV modes). The prompt is local to the form; it is not saved
  or sent with the carousel.
- Backend: `POST /api/carousels/cover-prompt-ideas` `{topic (3-500), palette?: {name, mode, background,
  primary, accent}, locale: pt|en}` → `{ideas: [...]}` (3-6). Unknown fields are rejected (422), colours
  are strict hex, the palette name rejects markup. Prompt in `agents/prompts/cover_prompt/v1/ideas.yaml`
  (topic delimited as data, sanitised; the model is told never to invent personal details). Every idea is
  re-checked: whitespace collapsed, 12-400 characters, no `< > { }`, no repeats (case-insensitive), at
  most six. Fewer than three usable ideas → one more call; still fewer, or the LLM failing / timing out
  (12 s each, so at most ~24 s) both times → 503 `cover_prompt_ideas_unavailable`. Editor or admin only; 10/minute per user.
  Langfuse trace: phase and agent `cover_prompt_ideas`, user id, content type `carousel`.

## Non-Goals

- The Grok cover dialog itself (AE-0508). Plugging the component into it is a follow-up PR once AE-0508
  is merged.
- Storing the prompt, or using it to generate an image in the create form.
- No new table, no migration.

## Acceptance Criteria

- [x] Given "Foto do slide 1" in a POV carousel, Then 3-6 suggested prompts (angle, background, mood)
      are shown, tailored to the selected palette's colours and the topic; the curated catalogue comes
      first and needs no network call.
- [x] Given a suggestion, When the owner taps it, Then it fills the prompt field, which stays editable.
- [x] Given a topic, When the owner presses "Mais ideias", Then `POST /api/carousels/cover-prompt-ideas`
      receives only the topic, the palette (or null) and the locale, and 3-6 server-checked AI ideas
      replace the list; personal fields are rejected with 422.
- [x] Given an LLM error, timeout or too few usable ideas, Then the API answers 503 and the field shows a
      retryable error while the curated suggestions stay; the endpoint requires an editor and is rate
      limited per user.
- [ ] Given the Grok cover dialog (AE-0508), Then the same suggestions are shown there (follow-up PR after
      AE-0508 merges).

## Gherkin Scenarios

See `backend/tests/features/cover_prompt_ideas_ae0509.feature` and
`frontend/tests/features/cover-prompt-ideas-ae0509.feature`.

## Affected Areas

- [x] Backend (new route, schema, service, prompt, constants; rate limit)
- [x] Frontend (`create-photo-section.tsx`, create page, new `CoverPromptField`, hook, schema, i18n)
- [x] API (OpenAPI artifact and route snapshot: `POST /api/carousels/cover-prompt-ideas`)
- [x] Tests
- Database: no change.

## Dependencies

AE-0508 for the dialog half (follow-up PR).

## Progress Log

### 2026-10-23

Ticket written from Pedro's decision. The Slide 1 photo field had no prompt field, so one was added
(editable, local, with a hint that it is not saved). Backend and frontend implemented with tests.

### 2026-10-24

Gates captured; Dev Complete for the Slide 1 half.

Review round 1 (#273): each LLM call times out after 12 s (two attempts stay under 25 s); AI ideas only show
for the topic and palette they answer and stay on screen while "Mais ideias" reloads; a "Copiar" button puts
the prompt on the clipboard until the AE-0508 follow-up wires the field into the Grok dialog; the request is
parsed client-side and the response must hold 3-6 ideas; docstrings say "only the topic and palette reach
the model".

## Files Touched

See `.agent/reports/AE-0509.dev-summary.md`.

## Test Evidence

See `.agent/reports/AE-0509.dev-summary.md`.

## QA Report

See `.agent/reports/AE-0509.qa.md`.

## Blockers

None for this PR. The dialog half waits for AE-0508.
