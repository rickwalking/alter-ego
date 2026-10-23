# AE-0527 — Owner archives a stale carousel; carousels idle for N days archive themselves

Status: In Development
Tier: T2
Priority: Medium
Type: Feature
Area: Cross-cutting
Owner: Claude Code (claude-opus-5-5)
Branch: feat/ae-0527-archive-stale-carousels
Created: 2026-10-23
Updated: 2026-10-23

## Goal

A carousel the owner has given up on leaves the active workflow board and stops raising alerts, either
because the owner archived it or because it sat idle for N days, and it can be restored at any time.

## Problem

Workflow alerts (CO-1): 15 prod carousels sit unfinished; the stuck-workflow alert keeps firing for them
and the owner has no way to close a project. Pedro's decision (2026-10-22): both an owner "Arquivar"
action (restorable, hidden from the board and from alerts) and an automatic archive after N days without
activity (N configurable, 30 by default). Pedro picks which of the 15 to archive once this ships.

(This ticket was triaged as AE-0496; that id was already taken by the dependency-CVE fix, #236.)

## Scope

- `carousel_projects.archived_at` (nullable, timezone-aware): set = archived. Alembic migration plus an
  idempotent deploy one-shot (`python -m rag_backend.scripts.carousel_archived_at --apply --verify`, run
  by `deploy.yml` like the palette timestamptz step), because prod does not run Alembic.
- `POST /api/carousels/{id}/archive` and `POST /api/carousels/{id}/restore` (owner or admin). Archive is
  refused with 409 and a reason for a published carousel or one whose phase is in progress. Restore
  clears `archived_at` and counts as activity (so it is not archived again the next day). Both are
  idempotent.
- Workflow board: archived carousels leave the columns; `GET /api/workflow-board?archived=true` lists only
  the archived ones (the "Arquivados" view).
- Workflow alerts (stuck workflow, failed carousel) skip archived carousels.
- Auto-archive: the workflow worker archives carousels that are not published, not in progress, not
  archived and not updated for `CAROUSEL_AUTO_ARCHIVE_DAYS` days (default 30; 0 turns it off).
- Board UI: "Arquivar" on each card with a confirmation; disabled with the reason while the phase is in
  progress and absent on published cards; an "Arquivados" toggle that lists archived cards with
  "Restaurar".

## Non-Goals

- Archiving blog posts.
- Deleting carousels.
- Archiving the 15 prod projects (Pedro chooses them after deploy, through the UI).
- Hiding archived carousels from the carousel list pages other than the workflow board.

## Acceptance Criteria

- [x] Given a carousel that is neither published nor in progress, When the owner chooses "Arquivar" on the
      board and confirms, Then it leaves the active board and appears under "Arquivados".
- [x] Given an archived carousel, When the owner chooses "Restaurar", Then it is back on the active board.
- [x] Given a carousel whose phase is in progress, Then "Arquivar" is disabled with the reason, and the API
      answers 409; a published carousel cannot be archived (409, no button).
- [x] Given an archived carousel stuck for days, Then no stuck-workflow or failure alert is raised for it.
- [x] Given a carousel idle for more than `CAROUSEL_AUTO_ARCHIVE_DAYS` (default 30), When the workflow
      worker ticks, Then it is archived; a published, in-progress or recently active carousel is not; 0
      turns auto-archive off.
- [x] Given another user's carousel, Then a non-admin cannot archive or restore it (403); unknown 404.
- [x] Given the prod database, Then the deploy one-shot adds `archived_at` (and its index) once and is a
      no-op when re-run; `--verify` fails when the column is missing.

## Gherkin Scenarios

- `backend/tests/features/carousel_archive_ae0527.feature`
- `backend/tests/features/carousel_archived_at_oneshot_ae0527.feature`
- `frontend/tests/features/workflow-board-archive-ae0527.feature`

## Affected Areas

- Backend: carousel ORM model, carousel archive routes, publishing read ACL (board), workflow alert service,
  workflow worker, settings, one-shot script.
- Frontend: workflow board page, kanban board card actions, i18n (pt, en).
- Database: new nullable column + index (Alembic + deploy one-shot).
- API: two new routes; `archived` query flag on the board; OpenAPI artifact regenerated.
- Deployment: `deploy.yml` runs the one-shot after the palette step.

## Dependencies

- Related: AE-0495 (stuck-workflow alert once per episode, merged).

## Progress Log

### 2026-10-23

Ticket written from the dashboard triage and Pedro's answer (owner archive + auto-archive after N days).

Finished on the laptop: rebased on main (Alembic revision re-chained on `c7d8e9f0a1b3`, the deploy step folded
into the shared one-shot failure check), the failure-rate alert leaves archived carousels out, route, board,
one-shot and deploy-order tests added, and the board UI built: "Arquivar" with a confirmation, disabled with
the reason while the phase runs, absent on published cards, an "Arquivados" toggle with "Restaurar".

## Files Touched

- backend: `models/carousel.py` (`archived_at` + index), `alembic/versions/aa4a5695681f_carousel_archived_at.py`,
  `infrastructure/database/carousel_archived_at.py` + `scripts/carousel_archived_at.py` (deploy one-shot),
  `api/routes/carousels/{archive.py,router.py}`, `api/schemas/carousel_archive.py`,
  `domain/{carousel_archive.py,constants/carousel_archive.py,protocols/carousel_archive.py}`,
  `api/routes/workflow_board.py`, `modules/publishing/{domain/projections.py,infrastructure/publishing_read_acl.py}`,
  `application/services/workflow_failure_alert_service.py`, `application/workers/workflow_workers.py`,
  `infrastructure/database/carousel_auto_archiver.py`, `infrastructure/config/settings.py`,
  `bootstrap/app_factory.py`; tests, features, route snapshot, `docs/architecture/openapi.json`.
- deploy: `.github/workflows/deploy.yml` (one-shot after the palette step, failure checked after stack up).
- frontend: `app/dashboard/workflow/{page.tsx,card-archive-action.tsx,types.ts}`, `constants/workflow.ts`,
  `schemas/neon-kanban.ts`, `modules/editorial-operations/board/workflow/{adapters/workflow-adapter.ts,components/*}`,
  `modules/editorial/{index.ts,workflow/hooks/use-workflow-kanban.ts}`, i18n pt/en, tests,
  `tests/features/workflow-board-archive-ae0527.feature`.

## Test Evidence

Backend: archive unit (10), routes + board integration (7), one-shot on Postgres (4) + CLI (4) + deploy order
(4); the 20 files touching the board, alerts, worker or Alembic head (149 tests) green against Postgres.
Frontend: workflow page, card action, adapter and board tests (125) green. Gates:
`.agent/reports/AE-0527.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
