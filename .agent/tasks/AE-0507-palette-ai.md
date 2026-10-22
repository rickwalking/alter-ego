# AE-0507 — Create a palette with AI

Status: In Progress
Tier: T2
Priority: Medium
Type: Feature
Area: Backend + Frontend
Owner: Claude Code (claude-opus-5-5)
Branch: feat/ae-0507-palette-ai
Created: 2026-10-22
Updated: 2026-10-22

## Goal

In the "Nova paleta" modal the owner describes a palette in words, gets three contrast-checked candidates
from one fast-queue LLM call, and picks one to pre-fill the form. Nothing is saved until "Criar paleta".

## Problem

Dashboard QA (DQ-C-01): there is no way to create a palette with AI. `api/routes/palettes.py` only lists,
creates, edits and archives; `palette-form-modal.tsx` has manual fields only.

## Scope

Pedro's decision (2026-10-22): a "Descreva a paleta" field in the New palette modal; one LLM call on the
fast queue (`LLM_MODEL_QUEUE_FAST`, through the container's fast LLM service) returns 3 contrast-checked
candidates; picking one pre-fills the form; nothing is saved until Criar.

- `POST /api/palettes/generate` `{description}` (3-300 chars) → `{candidates: [...]}` with up to 3
  candidates (name, primary, accent, background, mode, keywords, contrast ratios). Prompt in
  `agents/prompts/palette/v1/generate.yaml`; the description is delimited as data.
- Server-side validation of every candidate: strict hex, the palette name rules, keywords sanitised
  (brand keywords dropped, count/length capped); `mode` derived from the background luminance.
- WCAG AA: the slide ink (dark ink on a light background, white on a dark one — the template's rule) and
  the accent and the primary colours must each reach 4.5:1 against the background. A failing colour is
  repaired by mixing it towards black or white until it passes; a candidate that still fails is dropped.
- LLM error, timeout, unparsable answer or no valid candidate → 503 `palette_generation_unavailable`.
- Rate limited: 5 per minute per caller (the app's limiter keys by caller address).
- Modal (create only): textarea "Descreva a paleta", "Gerar" / "Gerar de novo", three candidate cards
  (swatch, name, contrast) with "Usar"; "Usar" fills name, colours, mode and keywords.

## Non-Goals

- No auto-save, no new table, no change to create/edit/archive.
- No AI in the edit modal.
- Cover images and slide rendering are untouched.

## Acceptance Criteria

- [ ] Given "Nova paleta", When the owner describes a palette and clicks "Gerar", Then
      `POST /api/palettes/generate` returns up to 3 candidates with name, primary, accent, background,
      mode and keywords, each validated server-side (schema, hex, name, keywords).
- [ ] Given a candidate, Then the slide ink/background, accent/background and primary/background pairs
      reach WCAG AA 4.5:1; a failing colour is repaired server-side and a candidate that cannot be repaired
      is never returned.
- [ ] Given candidates, When the owner clicks "Usar" on one, Then the manual form is pre-filled and nothing
      is saved until "Criar paleta".
- [ ] Given an LLM error/timeout/invalid answer, Then the API returns 503 and the modal shows a retryable
      error while manual creation still works; the endpoint is rate-limited (5/minute) and requires login.

## Gherkin Scenarios

See `backend/tests/features/palette_generate_ae0507.feature` and
`frontend/tests/features/palette-generate-ae0507.feature`.

## Affected Areas

- [x] Backend (`api/routes/palettes.py`, `api/schemas/palette.py`, new generation service, prompt)
- [x] Frontend (`palette-form-modal.tsx`, new generator section + hook, schema, i18n)
- [x] API (OpenAPI artifact: `POST /api/palettes/generate`)
- [x] Tests
- Database: no change.

## Dependencies

None.

## Progress Log

### 2026-10-22

Ticket written from Pedro's decision; failing tests first.

## Files Touched

See `.agent/reports/AE-0507.dev-summary.md`.

## Test Evidence

See `.agent/reports/AE-0507.dev-summary.md`.

## QA Report

See `.agent/reports/AE-0507.qa.md`.

## Blockers

None.
