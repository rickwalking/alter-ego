# AE-0494 — Owner can delete a photo from the photo library

Status: In Progress
Tier: T2
Priority: Medium
Type: Feature
Area: Backend + Frontend
Owner: Claude Code (claude-opus-5-5)
Branch: feat/ae-0494-delete-library-photo
Created: 2026-10-22
Updated: 2026-10-22

## Goal

The owner can delete one of their own photos from the private creator photo library (personal data). A photo
that a carousel still uses cannot be deleted, and the owner is told which carousels use it.

## Problem

Dashboard QA (DQ-X-02): the owner cannot remove a photo from the private creator-asset library.
`api/routes/carousels/creator_asset_library.py` and `creator_assets.py` expose GET/POST/PUT only, so a
personal photo stays on the server forever.

## Scope

Pedro's decision (2026-10-22): a photo in use by any carousel CANNOT be deleted until no carousel uses it;
show which carousels use it.

- `DELETE /api/carousels/creator-assets/{asset_id}` (owner only):
  - 204: the row is deleted and its stored WebP is removed (unless another row still points at the same
    bytes); the image URL then returns 404.
  - 409 `{"code": "creator_asset_in_use", "carousels": [{"id", "title"}]}` when a carousel uses the
    photo: as its creator asset, its slide-1 hook photo or its slide-1 cover (`slide_cover`). Nothing is
    deleted.
  - 403 for another user's photo (admins included: it is the owner's personal data), 404 for an unknown id,
    401 without login.
- Wizard "Foto do slide 1": each photo has "Excluir foto" with an inline confirm; on 409 the section lists
  the carousels (title, link to the carousel) that use it; after a delete the library refreshes and a
  deleted selection moves to the newest remaining photo.

## Non-Goals

- No soft-delete and no schema change.
- The publish page cover picker gets no delete button (it lists the same library; a deleted photo drops out
  when it refetches).
- Copies already staged inside a carousel's own render folder are not touched (a carousel that uses the photo
  blocks the delete anyway).

## Acceptance Criteria

- [ ] Given the owner's photo library in the wizard, When they delete a photo no carousel uses and confirm,
      Then `DELETE /api/carousels/creator-assets/{id}` removes the row and the private file, the image URL
      returns 404 and the photo leaves the list.
- [ ] Given another user (or an admin who is not the owner), Then the DELETE returns 403 and nothing is
      deleted; an unknown id returns 404; no login returns 401.
- [ ] Given a photo used by any carousel (creator asset, hook photo or slide-1 cover), When the owner deletes
      it, Then the API returns 409 with the carousels that use it, nothing is deleted, and the wizard shows
      those carousels.

## Gherkin Scenarios

See `backend/tests/features/creator_photo_delete_ae0494.feature` and
`frontend/tests/features/creator-photo-delete-ae0494.feature`.

## Affected Areas

- [x] Backend (`creator_asset_library.py`, `creator_asset_service.py`, `creator_asset_repository.py`)
- [x] Frontend (`create-photo-section.tsx`, `use-pov-photo.ts`, `use-creator-photos.ts`, i18n)
- [x] API (OpenAPI artifact: `DELETE /api/carousels/creator-assets/{asset_id}`)
- [x] Tests
- Database: no change.

## Dependencies

None.

## Progress Log

### 2026-10-22

Ticket written from Pedro's decision; failing tests first.

## Files Touched

See `.agent/reports/AE-0494.dev-summary.md`.

## Test Evidence

See `.agent/reports/AE-0494.dev-summary.md`.

## QA Report

See `.agent/reports/AE-0494.qa.md`.

## Blockers

None.
