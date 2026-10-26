# AE-0554 — Cover panel follow-up: owner-only upload, upload errors by cause, polling, one error string

Status: Review
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
6. Found while fixing 1: `GET cover-generations` went through `apiCall`, whose 403 sends the browser to
   /403. A non-owner on the publish page lost the page instead of seeing the not-owner note (since
   AE-0508). A successful upload whose reply did not parse also read as a network failure.

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
- `apiCallOwnerOnly(url, schema)` in `lib/api-client.ts`: a GET that keeps the 401 login redirect but
  not the 403 page redirect, used only by the owner-only generation list. `apiUpload` turns a reply that
  is not JSON or misses fields into `ApiError(500)`, like `apiCall`.
- A failed refetch after a successful load keeps the owner's form (stale data wins over the error).
- Two uploads in a row are both ticked once listed.
- pt/en copy.

## Non-Goals

- No backend change (the API already refuses non-owners), no change to the upload endpoint or its limits.

## Acceptance Criteria

- [x] Given a carousel the viewer does not own, Then the panel shows only the not-owner note: no "Enviar
      foto", no "Gerar capa", and nothing is uploaded.
- [x] While the generation list is loading, no upload or generate control is shown.
- [x] A 429 upload, a network failure and a 5xx each show their own message; a 4xx refusal shows the
      wizard's upload sentence.
- [x] The generation list polls only while a generation is pending.
- [x] `uploadFailed` exists once (`create.photo.uploadFailed`) in pt and en.
- [x] An uploaded photo is ticked only once the cover options list it, and never past 3.
- [x] A non-owner stays on the publish page (the list's 403 does not redirect to /403); a 401 still goes
      to the login page.

## Gherkin Scenarios

See `frontend/tests/features/cover-panel-follow-up-ae0554.feature`.

## Affected Areas

- [x] Frontend (`lib/api-client.ts`, `cover-generate-panel.tsx`, `cover-photo-upload-field.tsx`, `use-cover-photo-upload.ts`,
      `use-cover-generate-form.ts`, `use-cover-generation.ts`, types, i18n)
- Backend: no change. API: no change. Database: no change.

## Dependencies

AE-0551 (#287).

## Progress Log

### 2026-10-25

Ticket written from Pedro's review of #287; failing tests first. While fixing the owner-only point the
list's 403 page redirect showed up and is fixed here (it defeated the point). Independent review (WARN):
upload parse errors, stale data over a refetch error, two uploads in a row, one failure constant.

## Files Touched

See `.agent/reports/AE-0554.dev-summary.md`.

## Test Evidence

See `.agent/reports/AE-0554.dev-summary.md`.

## QA Report

See `.agent/reports/AE-0554.qa.md`.

## Blockers

None.
