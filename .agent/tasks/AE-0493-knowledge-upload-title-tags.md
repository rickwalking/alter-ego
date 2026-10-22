# AE-0493 — Knowledge upload keeps the typed title and tags

Status: Dev Complete
Tier: T2
Priority: High
Type: Bug
Area: Backend
Owner: Pedro Marins
Branch: fix/ae-0493-knowledge-upload-title-tags
Created: 2026-10-22
Updated: 2026-10-22

## Goal

A document uploaded from the Knowledge Base form keeps the title and the tags the owner typed.

## Problem

Dashboard QA (DQ-B-06): uploading a file with a title and tags on `/dashboard/knowledge` saves the
document under the file name and without tags. `POST /api/documents/upload` declares `title`, `tags`,
`scope` and `is_public` as plain function parameters next to the `UploadFile`, so FastAPI reads them
from the **query string**, while `use-upload.ts` sends them as **multipart form fields** next to the file.
The route never sees them and falls back to the file name.

## Scope

- `title`, `tags`, `scope` and `is_public` become `Form()` fields of the upload route (the multipart
  body the frontend already sends). Validation and defaults are unchanged: no title → the file name;
  tags are comma-separated, trimmed, empties dropped; an unknown scope → 400.
- A contract test posts the multipart body exactly as `use-upload.ts` builds it.

## Non-Goals

- Choosing the scope in the upload form, scope badge and filter (AE-0502).
- Changing how tags are stored (they stay a comma-joined `metadata.tags` string).

## Acceptance Criteria

- [x] Given the KB upload form, When a file is uploaded with a title and tags, Then the document's
      `title` is the typed title and its metadata carries the tags.
- [x] Given no title, Then the file name is used.
- [x] A contract test sends the multipart fields exactly as `use-upload.ts` does (`file`, `title`,
      `tags`).
- [x] `scope` and `is_public` are read from the same multipart body; an unknown scope still answers 400.

## Gherkin Scenarios

See `backend/tests/features/knowledge_upload_fields_ae0493.feature`.

## Affected Areas

- [x] Backend (`api/routes/documents.py`)
- [x] API (the upload's fields move from the query string to the multipart body; OpenAPI artifact)
- [x] Tests
- Frontend: no change (it already sends form fields).
- Database: no change.

## Dependencies

- Blocks: AE-0502 (scope at upload), AE-0503.

## Progress Log

### 2026-10-22

Cause confirmed in the code (query parameters vs multipart fields); failing contract test first.

## Files Touched

- backend/src/rag_backend/api/routes/documents.py
- backend/tests/integration/test_knowledge_upload_fields_ae0493.py (new)
- backend/tests/features/knowledge_upload_fields_ae0493.feature (new)
- docs/architecture/openapi.json

## Test Evidence

Contract test red first (3 of 4 failed on origin/main), green after the fix; knowledge safety net,
route snapshot and document endpoint tests green; full backend gate capture green (Postgres gates and
mutation in CI). Details: `.agent/reports/AE-0493.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
