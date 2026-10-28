# AE-0569 — Workflow board discovery: search, filters, sort and readable cards

Status: In Development
Tier: T2
Priority: High
Type: Feature / UX
Area: Frontend (workflow board) + backend ordering
Owner: Pedro
Agent Lane: developer → qa
Branch: feat/ae-0569-board-discovery
Kanban Card: TBD
Created: 2026-10-28

## Goal

The owner can find and narrow carousels on the desktop workflow board
(`/dashboard/workflow`): a search box, status filter chips with counts and a
stable sort, backed by a deterministic API order, with cards whose badges mean
something (semantic colors per `resolveWorkflowStatusVisual`), no blank
Rejected cards and no raw `**markup**` / `<strong>` leaking into titles.

Split PR B of the AE-0557 board rework Pedro ordered after the impeccable
critique (score 18/40; P1-1, P1-2, P1-4).

## Problem

- No search, filter or sort: finding one carousel among 37 active + 29
  archived means scanning 9 columns by eye.
- `board_projects()` in `backend/src/rag_backend/modules/publishing/infrastructure/board_rows.py`
  has no `ORDER BY`, so card order is random and can reshuffle on the 15s poll.
  `updated_at` is returned by the API but dropped by `mapApiKanbanColumn`, so
  the frontend cannot sort or show recency.
- Every card badge is hard-coded teal: "Needs review" (actionable) looks like
  "Approved". The semantic map (`resolveWorkflowStatusVisual`) already exists
  and the board ignores it.
- Rejected cards with empty title/topic render as a box holding only a
  "Brief" badge; titles render literal `**bold**` and `<strong>` markup;
  5 of 23 Published cards repeat the title as the description and all say
  "Ready to publish" under a "Published" header.

## Scope

- Backend: `board_projects()` adds
  `.order_by(CarouselProjectModel.updated_at.desc(), CarouselProjectModel.id)`
  (only backend change; `KanbanCardResponse` unchanged).
- `kanbanCardSchema`: `statusKey` (raw workflow status), `statusVariant`,
  `statusPulse` (filled by `localizeBoardColumns` from
  `resolveWorkflowStatusVisual`), `updatedAt` (from `card.updated_at`);
  `title` becomes a plain string (empty until localization substitutes the
  untitled fallback).
- `mapApiKanbanColumn`: keeps `updated_at`, keeps the raw status as
  `statusKey`, strips inline `**`/`__`/`<strong>`/`<em>`/`<b>`/`<i>` markup
  from title/topic, falls back title → topic → empty (localized later), and
  blanks a description equal to the title.
- `localizeBoardColumns`: substitutes the untitled title, fills
  `statusVariant`/`statusPulse`.
- Board toolbar (new `workflow-toolbar.tsx` + `use-board-filters.ts` +
  `board-filters.ts`): `NeonSearchBar` (title + topic, case- and
  accent-insensitive, `/` focuses), status chips with counts and
  `aria-pressed` (All / Needs review / In progress / Ready / Failed), sort
  Updated ↓ (default) / Title A-Z. Toolbar state lives in the URL
  (`?q=&status=&sort=`, defaults out of the URL, `router.replace`, Suspense
  boundary per the calendar page pattern).
- Board cards: `NeonBadge variant={statusVariant}` + `pulse` (the badge
  already guards `prefers-reduced-motion`), link `aria-label`
  `"<title>, <status>"`; the published column shows the relative updated time
  instead of the redundant "Ready to publish" badge; column headers show the
  actionable "need you" count (`awaiting_human`).

## Non-Goals

- Fixed-height board, rails, scroll restore, breadcrumb, prev/next (split PR
  A, AE-0568).
- Queue page move (split PR C, AE-0557).
- Keyboard roving tabindex, focus ring color, archive overflow menu,
  Ativos/Arquivados segmented control, List view (split PR D, AE-0570 and
  later polish).
- Columns with 0 matches collapsing to rails: belongs to the PR A board
  layout.

## Acceptance Criteria

- [ ] AC1 Given board rows with distinct `updated_at`, When the API returns
  them, Then cards are ordered newest first with a deterministic tiebreak on
  id, stable across polls.
- [ ] AC2 Given the toolbar, When the owner types in the search box, Then
  only cards whose title or topic match (case- and accent-insensitive)
  remain, counts update, and `/` focuses the box outside editable fields.
- [ ] AC3 Given the status chips, When one is pressed (`aria-pressed`), Then
  only cards whose raw status maps to that bucket remain (awaiting_human →
  Needs review; in_progress → In progress; approved/approved_for_publish →
  Ready; rejected/failed → Failed; All keeps everything) and the filter is in
  the URL.
- [ ] AC4 Given the sort control, When Title A-Z is chosen, Then cards sort
  by title; the default is Updated ↓; the choice is in the URL and survives
  reload and Back.
- [ ] AC5 Given any card, Then its badge uses the semantic variant and pulse
  from `resolveWorkflowStatusVisual` (awaiting_human magenta, in_progress
  cyan pulsing, approved/ready teal, published green, rejected/failed red).
- [ ] AC6 Given a Rejected card with empty title and topic, Then its title is
  the localized "Sem título" fallback; given a title with `**` or
  `<strong>` markup, Then the markup is stripped; given description ===
  title, Then the description is empty.
- [ ] AC7 Given the Published column, Then no card shows "Pronto para
  publicar"; the card shows the relative updated time instead.
- [ ] AC8 Given a column with awaiting_human cards, Then its header shows the
  "need you" count.

## Gherkin Scenarios

- `frontend/tests/features/board-discovery-ae0569.feature`

## References

- Critique: `/home/pmarins/alter-ego-qa/2026-10-26-board-critique/CRITIQUE.md`
  (P1-1, P1-2, P1-4, P3 published badge).
- Files: `board_rows.py`, `neon-kanban.ts`, `workflow-adapter.ts`,
  `localize-board.ts`, `neon-kanban-board.tsx`, `workflow/page.tsx`, new
  toolbar files.

## Dev Notes

- Decisions attributed to Pedro (critique follow-up, 2026-10-26).
- i18n keys in pt/en: `workflow.board.searchPlaceholder`,
  `workflow.board.filters.*`, `workflow.board.sort.*`, `workflow.board.needYou`,
  `workflow.board.updatedAgo` if needed; reuse `workflow.queue.untitled`.
- No comments in source (JSDoc/docstrings only); types colocated in
  `types.ts` under `src/modules/**`; every interactive element gets a
  `:focus-visible` style; animations guarded by `prefers-reduced-motion`.
