# AE-0536 — Retry clears both knowledge namespaces; a run claim always restores an archived carousel

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0536-knowledge-clear-other-namespace
Created: 2026-10-23
Updated: 2026-10-23

## Goal

No chunk of a knowledge document lingers in the scope it never got, and a carousel the owner starts working
on never stays archived because an automatic archive raced the work.

## Problem

Review follow-ups to AE-0534 (#259) and AE-0527 (#258).

1. Privacy. When a scope change fails after re-indexing and the cleanup (`drop_chunks`) fails too, the chunks
   stay in the NEW namespace (for example `public`) while the document rolls back to `personal`, FAILED. The
   Retry (reprocess) cleared only the current scope's namespace, and delete did the same, so the leftover
   public chunks stayed searchable by the public chat.
2. Race. The un-archive guard read `archived_at` from the request's already-loaded object. An automatic archive
   that committed in between left the carousel archived while a run started on it. The resume claim is a raw
   `lock_version` CAS UPDATE that the ORM guard does not see at all.

## Scope

- `DocumentProcessingPipeline`: reprocess, rescope and delete clear the document's chunks from its own scope's
  namespace and from the `personal` and `public` namespaces.
- `OptimisticLockService.bump_carousel_version` (the run and edit claim) clears `archived_at` in its CAS UPDATE.
- The ORM un-archive guard always writes `archived_at = NULL` on activity, whatever the loaded value says.

## Non-Goals

- Changing what a scope change or a reprocess indexes.
- Changing the archive rules or the board.

## Acceptance Criteria

- [x] Given a personal document whose move to public failed after indexing and whose cleanup failed, When the
      owner retries it, Then none of its chunks are left in `public` and it is indexed again in `personal`.
- [x] Given a document with chunks left in both namespaces, When it is deleted, Then none remain; other
      documents' chunks stay.
- [x] Given a carousel archived after a request loaded it, When the request claims a run through the
      `lock_version` CAS, Then the carousel is no longer archived.
- [x] Given a carousel archived after a request loaded it, When the request saves an edit through the ORM,
      Then the carousel is no longer archived.

## Gherkin Scenarios

- `backend/tests/features/knowledge_clear_other_namespace_ae0536.feature`
- `backend/tests/features/carousel_archive_race_ae0536.feature`

## Affected Areas

- Backend: `application/services/document_pipeline.py`, `application/services/optimistic_lock_service.py`,
  `infrastructure/database/carousel_archive_guard.py`.
- Frontend: none. Database: none. API: none.
- Tests: knowledge integration (real routes, Unit of Work, session and `PineconeVectorStore` over the in-memory
  index), carousel archive unit tests.

## Dependencies

- Blocked by: AE-0534 (#259) and AE-0527 (#258), both merged.
- Blocks: none.

## Progress Log

### 2026-10-23

Ticket written from the reviews of #259 and #258. Implemented: the pipeline clears both selectable namespaces;
the lock_version CAS clears `archived_at`; the guard writes `archived_at = NULL` unconditionally on activity.
The old code fails the new knowledge integration tests (2 of 2) and the race tests (2 of 2).

## Files Touched

- backend: `application/services/document_pipeline.py`, `application/services/optimistic_lock_service.py`,
  `infrastructure/database/carousel_archive_guard.py`; tests
  `tests/integration/test_knowledge_clear_other_namespace_ae0536.py`,
  `tests/unit/application/test_carousel_archive_quiet_ae0527.py` (race tests; the ORM lock_version test is
  renamed), updated namespace expectations in the AE-0502 scope tests; features.

## Test Evidence

Knowledge and archive test files (26 files, 245 tests) green after the rebase on main. Gates: `.agent/reports/AE-0536.dev-summary.md`.

## Decision Log

- 2026-10-23 — Reviewer: Retry must also clear the other scope's namespace (privacy), and the run claim's
  UPDATE must clear `archived_at` rather than an ORM guard reading a possibly stale value.

## QA Report

Pending.

## Blockers

None.
