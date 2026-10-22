# AE-0475 — Knowledge documents stuck "pending · 0 chunks" with no error or retry

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Backend + Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-23
Branch: fix/ae-0475-knowledge-ingestion-state
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Knowledge ingestion never sticks silently: failed or stuck documents show the reason and a Retry action, and the
backend saves processing failures.

## Problem

Found by the AE-0453 site scan (SITE-23): `/dashboard/knowledge` listed `my_resume.pdf` twice, both "pending · 0
chunks" since 2026-06-02, with no error or way to recover. Causes in the code:

- `POST /api/documents` (the "New Document" form) only creates the row (`status=pending`); despite its docstring
  nothing ever processes it.
- A failed reprocess marked the document failed and re-raised, so the request's Unit of Work rolled the failure back:
  the document went back to its previous state and the reason was lost (HTTP 500).
- The card showed the raw status, "N chunks" and the delete label in English, and had no retry.

## Scope (owner decision 2026-10-22: error state + reason + Retry; backend marks failures)

- Backend: `DocumentProcessingPipeline.reprocess_document` records a failure (status `failed`, reason = a fixed code
  naming the step that failed: `embedding_unavailable`, `vector_store_unavailable`, `empty_content` or
  `processing_error`; the error text is only logged, never saved or returned) and returns it, so the Unit of Work commits it; `process_document`
  (upload/ingest) keeps raising so a failed upload still rolls back (existing contract). Create route docstring
  corrected.
- Frontend: document card shows the localized status, the failure reason, a "Processing did not finish." notice for
  pending/processing documents untouched for over 10 minutes, and a Retry button (existing reprocess endpoint) for
  failed or stale documents; "New Document" starts processing right after the create. The card translates the reason
  code (an unknown/older free-text reason shows as the generic processing error), a failed retry shows an inline
  error on its card, and each document's retry is tracked on its own.

## Non-Goals

- Deleting the two stuck prod rows (the orchestrator does it).
- Background job queue for processing.

## Acceptance Criteria

- [x] A failed reprocess answers 200 with `status=failed` + reason and the stored row shows the same.
- [x] A successful reprocess clears an earlier failure; a failed upload still rolls back.
- [x] Failed/stale cards show the reason/notice and Retry; fresh/completed cards do not.
- [x] Status, chunk count and delete label localized (en/pt).
- [x] New documents are processed right after creation.
- [x] The saved/returned reason is a fixed code, never the error text (review finding: provider errors can carry
      hosts, URLs, key fragments); the card shows it in words.
- [x] A failed retry shows an inline error; retrying A then B keeps A busy until A's own request settles.

## Repro Steps

1. Create a document with "New Document". Before: it stays "pending · 0 chunks" forever. After: processed; on
   failure "Failed" + reason + Retry.

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

Touches `knowledge-base-interface.tsx` like AE-0464 (#202): trivial rebase for whichever lands second.

## Progress Log

### 2026-10-22 08:10

Root causes from the code; failing tests first (pipeline 2 red, card 4 red); fix.

### 2026-10-22 (AE-0481 shepherd)

Rebased onto main (kept #221's `add_note(PIPELINE_FAILURE_LOGGED)`, #202's `useIsClient` skeleton). Review fixes:
fixed reason codes by failing step, translated on the card; `useDocumentRetries` (per-id retrying/failed sets,
`mutateAsync` so every call settles its own id) with an inline retry error.

## Files Touched

- backend/src/rag_backend/application/services/document_pipeline.py
- backend/src/rag_backend/domain/constants/documents.py (failure reason codes)
- backend/src/rag_backend/api/routes/documents.py (docstring)
- backend/tests/unit/application/test_document_pipeline_failures_ae0475.py (new)
- backend/tests/integration/test_knowledge_reprocess_failure_ae0475.py (new)
- backend/tests/features/knowledge_ingestion_failure_ae0475.feature (new)
- frontend/src/modules/knowledge/components/document-card.tsx, document-state.ts (new), document-list.tsx,
  knowledge-base-interface.tsx, types.ts (+ document-card-state.test.tsx new, document-card.test.tsx,
  knowledge-base-interface.test.tsx)
- frontend/src/modules/knowledge/hooks/use-document-retries.ts (+ test, new), hooks/types.ts
- frontend/src/i18n/locales/en.json, pt.json
- frontend/tests/features/knowledge-document-state-ae0475.feature (new)

## Test Evidence

See PR. Mutation: CI only (AE-0448).

## QA Report

Pending (CI on the PR head).

## Blockers

None.
