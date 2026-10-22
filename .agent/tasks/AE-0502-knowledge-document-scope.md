# AE-0502 — Knowledge Base shows and sets each document's scope (Pessoal / Público)

Status: In Development
Tier: T2
Priority: Medium
Type: Feature
Area: Cross-cutting
Owner: Claude Code (claude-opus-5-5)
Branch: feat/ae-0502-knowledge-document-scope
Created: 2026-10-22
Updated: 2026-10-22

## Goal

The owner sees whether each knowledge document is personal or public, chooses the scope when adding a
document (personal by default), filters the list to public knowledge, and can change a document's scope
later.

## Problem

Dashboard QA (DQ-B-05): `/dashboard/knowledge` shows neither `scope` nor `is_public` on a document card,
the upload and create forms never send a scope (every document lands as `personal`), and there is no way
to list public knowledge or to move a document between scopes. Pedro's decision: per-document scope at
upload, Pessoal by default, Público as the alternative, a badge and a filter, and the scope can be changed
later.

The scope picks the Pinecone namespace the document's chunks are indexed in (`personal` or `public`).
Today the visitor chat searches both namespaces (`hybrid_retriever._resolve_namespaces`), so the copy
must not claim that a Pessoal document is hidden from the chat.

## Scope

- Document card: a scope badge, "Pessoal" or "Público".
- Upload form and text-document form: a scope choice (Pessoal default, Público); the request carries
  `scope` and the matching `is_public`.
- Document list: a scope filter (Todos / Pessoal / Público) next to the search.
- `PATCH /api/documents/{document_id}/scope` (`{"scope": "personal" | "public"}`): owner or admin only;
  drops the document's chunks from the old namespace, sets `scope` (and `is_public` to match), and
  re-indexes the document under the new namespace. Any other scope answers 400; an unknown document 404.
- Document card: a "Tornar público" / "Tornar pessoal" action that calls it.

## Non-Goals

- Changing which namespaces the visitor chat searches (raised with Pedro as a separate decision).
- Server-side scope filtering or pagination of the document list (the list stays one client-filtered page,
  like the existing search box).
- Choosing the `carousel` / `internal` system scopes from the UI.
- A database schema change (`documents.scope` and `documents.is_public` already exist).

## Acceptance Criteria

- [ ] Given a document, Then its card shows a "Pessoal" or "Público" badge from its `scope`.
- [ ] Given the upload form, Then the owner can choose Pessoal (default) or Público, and the multipart
      upload carries `scope` and `is_public` accordingly.
- [ ] Given the text-document form, Then the same choice is offered and the create request carries it.
- [ ] Given the scope filter set to Público, Then only public documents are listed (Pessoal likewise;
      Todos lists both); the filter combines with the search box.
- [ ] Given a document, When the owner changes its scope, Then `PATCH /api/documents/{id}/scope` moves its
      chunks from the old namespace to the new one, the document comes back with the new scope and
      `is_public`, and the card shows the new badge.
- [ ] Given the PATCH, When the scope is not `personal`/`public` Then 400; an unknown document 404; a
      non-owner non-admin 403; anonymous 401; the same scope is a no-op that does not re-index.

## Gherkin Scenarios

- `backend/tests/features/knowledge_document_scope_ae0502.feature`
- `frontend/src/modules/knowledge/knowledge-document-scope.feature`

## Affected Areas

- Backend: `api/routes/documents.py`, `api/schemas/documents.py`, knowledge facade (`modules/knowledge`),
  `application/services/document_pipeline.py`.
- Frontend: `modules/knowledge/components/*`, `hooks/use-upload.ts`, `hooks/use-documents.ts`,
  `constants/api.ts`, i18n (pt, en).
- Database: no change.
- API: new `PATCH /api/documents/{document_id}/scope`; OpenAPI artifact regenerated.
- Tests: backend unit + integration, frontend component/hook tests.

## Dependencies

- Blocked by: AE-0493 (merged: the upload reads scope from the multipart body).
- Blocks: AE-0503 (Pedro uploads his CV, bio and blog posts as Público).

## Progress Log

### 2026-10-22

Ticket written from the dashboard triage and Pedro's answer (per-document scope, Pessoal default,
badge + filter, changeable later). Confirmed in the code that both namespaces feed the visitor chat.

## Files Touched

## Test Evidence

## QA Report

Pending.

## Blockers

None.
