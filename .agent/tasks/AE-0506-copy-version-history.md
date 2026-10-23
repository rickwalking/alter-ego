# AE-0506 — Version history for the caption and the LinkedIn posts

Status: Dev Complete
Tier: T2
Priority: Medium
Type: Feature
Area: Backend + Frontend + Database
Owner: Pedro Marins
Branch: feat/ae-0506-copy-version-history
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Every saved edit of a carousel's Instagram caption or LinkedIn post (PT/EN) is kept as a version (who,
when, which text, the text), and the owner sees the versions of a text and can restore one.

## Problem

Dashboard QA (DQ-D-15): AE-0492 and AE-0505 save the caption and the LinkedIn posts in place; the
previous text is gone after a save and nobody can see who changed it. Pedro (Q8) keeps the approval when
an approved carousel's text is edited, on the condition that the edit is recorded as a version.

The `content_versions` table exists (unused) but its unique index is global on
`(content_type, version_number)`: two carousels cannot both have a version 1, so it cannot hold
per-carousel histories as is. Prod (bootstrapped by `create_all`, no Alembic) has the table, empty, with
that index.

## Scope (Pedro, 2026-10-22, Q9: reuse `content_versions`, fix its unique index via a deploy one-shot)

- The unique index becomes `(content_id, content_type, version_number)`: model, Alembic migration, and
  an idempotent deploy one-shot (`content_versions_index`, palette_timestamptz pattern: drop the old
  global index if present, create the per-content one if absent, `--verify` gates the deploy).
- Each save through `PATCH /api/carousels/{id}/copy` writes one version per changed text, in the same
  transaction as the text: `content_type = "carousel_copy"`, `content_id` = the carousel id, numbered per
  carousel, `snapshot = {field, text}`, the author and the time. The first edit of a text also stores the
  text it replaces (no author: the generated text) so the original can be restored. An unchanged text
  writes no version.
- `GET /api/carousels/{id}/copy/versions` (owner or admin) lists the versions, newest first, with the
  author's name.
- `POST /api/carousels/{id}/copy/versions/{n}/restore` (owner or admin, `If-Match`) saves that version's
  text through the same save path (same guards: lock version, run in progress, published caption), which
  itself records a new version ("restored from version n").
- UI: a "Histórico" list under the caption and the LinkedIn editors (publish page and Revisão final):
  each version shows who, when and the text; "Restaurar" restores it (disabled while that text has
  unsaved edits).

## Non-Goals

- Versions of slides, the blog body (it has its own history) or `caption_en`.
- Diffs between versions.
- Pruning old versions.

## Acceptance Criteria

- [x] Given a save that changes the caption, Then one `carousel_copy` version with the field, the new
      text, the author and the time is stored with the save (same transaction); the first edit of a
      text also stores the replaced text as the original version.
- [x] Given a save that changes nothing in a text, Then no version is written for it.
- [x] Given two carousels, Then each numbers its versions from 1 (the unique index is per content).
- [x] Given the versions route, Then the owner or an admin gets them newest first with who/when/field/
      text; anyone else gets 403.
- [x] Given a restore of version n with the current lock version, Then the text becomes version n's,
      a new version "restored from version n" is stored, and the lock version advances; a stale lock is
      409 `version_conflict`; an unknown version is 404; a published caption is 409.
- [x] Given prod, Then the deploy runs `python -m rag_backend.scripts.content_versions_index --apply
      --verify` after the blog cutover; re-running it changes nothing; `--verify` fails while the old
      global index is present or the per-content one is missing.
- [x] Given the publish page or Revisão final, Then the "Histórico" of the caption and of the LinkedIn
      posts lists the versions and "Restaurar" restores one (then the texts and lock version refresh).

## Gherkin Scenarios

See `backend/tests/features/carousel_copy_versions_ae0506.feature` and
`frontend/tests/features/copy-version-history-ae0506.feature`.

## Affected Areas

- [x] Backend (copy edit service, new copy history service + version store, routes, schemas, constants)
- [x] Database (`content_versions` unique index: model, Alembic, deploy one-shot + deploy.yml step)
- [x] Frontend (history list, hooks, publish page and final review wiring, i18n)
- [x] API (two new routes; OpenAPI artifact, route snapshot)
- [x] Tests

## Dependencies

- Depends on: AE-0492 (copy write route), AE-0505 (final review editors).

## Progress Log

### 2026-10-22

Ticket written from the dashboard QA triage; Pedro's Q8/Q9 answers applied. Prod checked read-only:
`content_versions` is empty and has the global `(content_type, version_number)` unique index.

## Files Touched

See `.agent/reports/AE-0506.dev-summary.md`.

## Test Evidence

Failing first: the 9 route tests answered 404 before the routes existed. Full backend (with Postgres)
and frontend gate captures green; mutation in CI. See the dev summary.

## QA Report

## Blockers

None.
