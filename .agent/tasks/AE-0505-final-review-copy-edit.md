# AE-0505 — Edit the caption and LinkedIn posts in the final review step

Status: In Progress
Tier: T2
Priority: Medium
Type: Feature
Area: Frontend
Owner: Pedro Marins
Branch: feat/ae-0505-final-review-copy-edit
Created: 2026-10-22
Updated: 2026-10-22

## Goal

In "Revisão final" of the create workspace the reviewer edits and saves the Instagram caption and the
LinkedIn post (PT and EN), and the saved text is what the publish page shows, copies and publishes.

## Problem

Dashboard QA (DQ-D-14): the final review step shows the caption read-only, has no LinkedIn tab, and shows
the blog as a markdown dump with no way to reach the blog editor. The only place to fix a caption is the
publish page (AE-0492). The final review "Legenda" tab also reads the caption from the workflow checkpoint,
so a text saved on the publish page is not what the review shows.

## Scope (Pedro, 2026-10-22, Q8)

- "Legenda" and a new "LinkedIn" tab (PT/EN) in Revisão final are editable with an explicit Save, through
  the AE-0492 route `PATCH /api/carousels/{id}/copy` (If-Match lock version). Same editor, limits and
  save states as the publish page.
- The tabs show the saved project texts (the publish page's rule: saved project text first, checkpoint
  text as the fallback), so both pages show the same text.
- After a save the workflow state and the project are refetched, so the approve / request-changes
  controls send the new lock version.
- The blog body stays in the blog editor: the Blog tab keeps its preview and gets an "Abrir no editor do
  blog" action (opens the carousel's blog post; creates the draft when there is none yet).
- Editing after approval keeps the approval (Pedro, Q8 (i)); the backend already keeps it (AE-0492
  scenario "Saving the texts keeps the carousel approved for publish"). Recording a version of each edit is
  AE-0506.

## Non-Goals

- Version history of the texts (AE-0506).
- Editing `caption_en` or the blog body inline in the review step (Pedro chose Q8 (a)).
- Backend changes: the write route, its guards and the approval behaviour come from AE-0492.

## Acceptance Criteria

- [ ] Given Revisão final, When the reviewer opens "Legenda", Then the caption is in an editor with the
      Instagram limits and a Save button; saving sends `PATCH /copy` with the workflow lock version and
      shows "Salvo".
- [ ] Given Revisão final, When the reviewer opens "LinkedIn", Then the PT and EN posts are editable per
      language and saved the same way.
- [ ] Given a saved text, Then the final review tab and the publish page show that text (project text
      first, checkpoint text only when the project has none).
- [ ] Given a save, Then the workflow state and the project are refetched (the next approve sends the new
      lock version); a stale-lock refusal shows the stale message and refetches.
- [ ] Given unsaved edits, When the reviewer switches tab, Then the drafts stay; When they leave by an
      in-app link, Then the styled leave dialog asks first.
- [ ] Given the Blog tab, Then it keeps the preview and offers "Abrir no editor do blog", which opens the
      carousel's blog post in the blog editor.
- [ ] Given an approved carousel at final review, When the caption is edited and saved, Then it stays
      approved (backend behaviour from AE-0492, unchanged).

## Gherkin Scenarios

See `frontend/tests/features/final-review-copy-edit-ae0505.feature`.

## Affected Areas

- [ ] Frontend (`create-final-review-tabs.tsx`, `final-review-phase-review.tsx`, `create-phase-review.tsx`,
      `create-workflow-panel.tsx`, publishing module copy editor exports, blog editor entry, i18n)
- [ ] Tests
- Backend: no change. Database: no change.

## Dependencies

- Depends on: AE-0492 (copy write route and the publish page editor).
- Related: AE-0506 (version history).

## Progress Log

### 2026-10-22

Ticket written from the dashboard QA triage; Pedro's Q8 answer applied.

## Files Touched

## Test Evidence

## QA Report

## Blockers

None.
