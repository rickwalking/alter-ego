# AE-0554 — Cover panel follow-up: owner-only upload, upload errors by cause, polling, one error string

Status: In Development
Tier: T1
Priority: Medium
Type: Bugfix
Area: Frontend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0554-cover-panel-follow-up
Created: 2026-10-25
Updated: 2026-10-25

## Goal

Close the review findings on the AE-0551 cover panel (#287), per Pedro's review.

## Problem

1. "Enviar foto" and "Gerar capa" render while the generation list loads, so an admin on someone else's
   carousel can upload a photo into the admin's own library; the generation then fails 403
   `cover_generation_not_owner`.
2. Every refused upload reads as a type/size problem, including a 429 rate limit and a network failure.
3. `useCoverGenerations(projectId, true)` takes an `enabled` argument that is now always true. The list is
   polled only while a generation is pending (the interval stops otherwise, and the app's query client
   does not refetch on focus); no test pinned that.
4. `publish.coverPicker.generate.uploadFailed` duplicates `create.photo.uploadFailed` in pt and en.
5. A freshly uploaded photo is ticked before the cover options refetch lists it, so it counts toward the
   3 while it is invisible in the checklist.

## Scope

- The panel shows its form (photos, "Enviar foto", prompt, "Gerar capa") only once the owner's generation
  list has loaded; a 403 shows the not-owner note, as before, and nothing else.
- Upload errors by cause: 429 → "too many uploads, wait a minute"; network failure (no HTTP answer) →
  "check your connection"; 5xx → "the server could not store it, try again"; any other refusal (4xx: type,
  size, validation) → the wizard's sentence `create.photo.uploadFailed`, read from that key (the copy under
  `publish.coverPicker.generate` is removed).
- `useCoverGenerations(projectId)` drops the argument; tests pin that the list refetches on an interval
  only while a generation is pending.
- A just-uploaded photo waits until the refetched options list it, then is ticked (still only while fewer
  than 3 are ticked).
- pt/en copy.

## Non-Goals

- No backend change (the API already refuses non-owners), no change to the upload endpoint or its limits.

## Acceptance Criteria

- [ ] Given a carousel the viewer does not own, Then the panel shows only the not-owner note: no "Enviar
      foto", no "Gerar capa", and nothing is uploaded.
- [ ] While the generation list is loading, no upload or generate control is shown.
- [ ] A 429 upload, a network failure and a 5xx each show their own message; a 4xx refusal shows the
      wizard's upload sentence.
- [ ] The generation list polls only while a generation is pending.
- [ ] `uploadFailed` exists once (`create.photo.uploadFailed`) in pt and en.
- [ ] An uploaded photo is ticked only once the cover options list it, and never past 3.

## Gherkin Scenarios

See `frontend/tests/features/cover-panel-follow-up-ae0554.feature`.

## Affected Areas

- [ ] Frontend (`cover-generate-panel.tsx`, `cover-photo-upload-field.tsx`, `use-cover-photo-upload.ts`,
      `use-cover-generate-form.ts`, `use-cover-generation.ts`, types, i18n)
- Backend: no change. API: no change. Database: no change.

## Dependencies

AE-0551 (#287).

## Progress Log

### 2026-10-25

Ticket written from Pedro's review of #287; failing tests first.

## Files Touched

See `.agent/reports/AE-0554.dev-summary.md`.

## Test Evidence

See `.agent/reports/AE-0554.dev-summary.md`.

## QA Report

See `.agent/reports/AE-0554.qa.md`.

## Blockers

None.
