# AE-0501 — Knowledge Base lists the carousels' content sources

Status: In Development
Tier: T2
Priority: High
Type: Feature
Area: Cross-cutting
Owner: Claude Code (claude-opus-5-5)
Branch: feat/ae-0501-knowledge-carousel-sources
Created: 2026-10-22
Updated: 2026-10-23

## Goal

The owner sees, in the Knowledge Base, every content source attached to their carousels and can open the
carousel each source belongs to.

## Problem

Dashboard QA (DQ-B-04): `/dashboard/knowledge` lists only uploaded documents
(`frontend/src/modules/knowledge/queries.ts` reads `/api/documents` only). The content sources owners add
to their carousels (`content_sources`, read per carousel through `/api/projects/{id}/sources`) appear
nowhere in the Knowledge Base. Pedro's decision: a second, read-only tab "Fontes dos carrosséis" that
links to each carousel; the chat's knowledge stays as it is.

## Scope

- `GET /api/knowledge/carousel-sources` (editor or admin): the caller's carousel content sources, newest
  first, each with its title, type, URL (for a `url` source), date and carousel (id + title); paginated
  (`limit` 1-100, default 20, `offset`), filterable by `project_id`; the response also lists the carousels
  that have sources (id, title, count) for the filter. A non-admin sees only their own carousels'
  sources; an admin sees all.
- Knowledge Base page: two tabs, "Documentos" (unchanged) and "Fontes dos carrosséis".
- The sources tab: a read-only list (title, type, URL link, carousel link to
  `/dashboard/create/{id}`, date), a carousel filter, previous/next pagination, an empty state.

## Non-Goals

- Ingesting carousel sources into Pinecone or any change to what the chat knows (Pedro: chat knowledge
  unchanged).
- Editing or deleting sources from the Knowledge Base (it stays read-only; editing happens on the carousel).
- The scouted `research_sources` rows (only owner-added `content_sources`).
- The "which consumer uses each document" label on the Documents tab (the Documents tab is unchanged).
- A database schema change.

## Acceptance Criteria

- [x] Given carousels with content sources, When the owner opens the "Fontes dos carrosséis" tab, Then each
      source is listed with its title, type, date and a link to its carousel (and its URL for a URL source).
- [x] Given the Documents tab, Then it is unchanged.
- [x] Given more sources than a page, Then the list paginates (next/previous, "x–y de N").
- [x] Given the carousel filter, When a carousel is chosen, Then only that carousel's sources are listed.
- [x] Given another owner's carousel, Then its sources are never listed for a non-admin; an admin sees all.
- [x] Given no sources, Then the tab shows an empty state.
- [x] Given an anonymous caller, Then the endpoint answers 401.

## Gherkin Scenarios

- `backend/tests/features/knowledge_carousel_sources_ae0501.feature`
- `frontend/tests/features/knowledge-carousel-sources-ae0501.feature`

## Affected Areas

- Backend: `api/routes/sources.py`, `api/schemas/knowledge_sources.py` (response models).
- Frontend: `modules/knowledge` (tabs, sources list, query), `constants/api.ts`, i18n (pt, en).
- Database: no change.
- API: new `GET /api/knowledge/carousel-sources`; OpenAPI artifact regenerated.
- Tests: backend integration, frontend component/query tests.

## Dependencies

- Related: AE-0502 (same Knowledge Base page).

## Progress Log

### 2026-10-22

Ticket written from the dashboard triage and Pedro's answer (second read-only tab linking to each
carousel; chat unchanged).

### 2026-10-23

Finished on the laptop: rebased on main, the pager is hidden when the chosen carousel has no sources (no
"1–0 of 0"), and ticket ids removed from test emails and docstrings. Backend and frontend gates for the
touched files re-run one by one.

## Files Touched

- backend: `api/routes/sources.py`, `api/dependencies/carousel_access.py` (owner-scoped listing query, no
  new import edge), `api/schemas/knowledge_sources.py` (new), tests
  (`test_knowledge_carousel_sources_ae0501.py`, `test_carousel_source_listing_ae0501.py`), feature,
  route snapshot, `docs/architecture/openapi.json`.
- frontend: `modules/knowledge/components/carousel-sources-panel.tsx` (new), `knowledge-base-interface.tsx`
  (tabs), `queries.ts`, `components/types.ts`, `schemas/knowledge.ts`, `constants/knowledge-sources.ts`
  (new), `constants/api.ts`, i18n pt/en, tests, `tests/features/knowledge-carousel-sources-ae0501.feature`.

## Test Evidence

Red first: the backend integration test failed 9 of 9 before the route. Green after: 9 integration + 3
unit; carousel access/authz suites (62) green; frontend `src/modules/knowledge` 112 green; eslint and tsc
clean. Details: `.agent/reports/AE-0501.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
