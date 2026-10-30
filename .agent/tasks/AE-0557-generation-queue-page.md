# AE-0557 — Generation queue on its own page with links to the carousels

Status: In Development
Tier: T2
Priority: High
Type: Feature / UX
Area: Frontend (dashboard, generation queue)
Owner: Pedro
Agent Lane: developer → qa
Branch: feat/ae-0557-generation-queue-page
Kanban Card: TBD
Created: 2026-10-28

## Goal

The generation queue (the Fila panel: status, metrics, rows and actions incl.
Reprocessar and Processar fila agora) lives on its own admin-only dashboard
page `/dashboard/queue` with a "Fila" nav item, the workflow board keeps only
a compact queue summary chip linking to it, and every queue row whose run has
a carousel links to that carousel's detail page.

Pedro, verbatim: "The status and items of the queue should have its own page,
also, use impeccable critique to refine the desktop version of the board.
(very bad to navigate around carousel items). The list of queue items should
link to the carousel details page."

## Problem

- The queue panel sits above the board and, with five queued runs plus parked
  runs plus backlog, pushes the board below the fold (critique P1-5); it also
  mixes mutating actions into a navigation page.
- Queue rows only link to the carousel editor through a small "openEditor"
  link on parked runs that cannot retry; the theme title (the natural link
  target) is plain text, and active runs have no link at all.

## Scope

- `DASHBOARD_ROUTES.QUEUE = "/dashboard/queue"`; new
  `app/dashboard/queue/{layout.tsx,page.tsx}` (pageMetadata("queue") pattern;
  `queue` joins the PageTitleKey union and `pageTitles` in PT/EN).
- Move `queue-panel*.tsx`, `queue-backlog-row.tsx`, `queue-reprocess-button.tsx`,
  `queue-row-action.tsx`, `queue-row-utils.ts`, their tests/test-utils, and the
  queue part of `workflow/types.ts` into `app/dashboard/queue/` (imports
  updated; the panel component itself is unchanged behavior).
- Sidebar: "Fila" item right after Workflow Board in sectionContent with
  `access: "admin"` (admins only, like the panel's 403-latched data); i18n
  `common.sidebar.queue` ("Fila" / "Queue").
- Queue page: NeonTopBar with the queue title/subtitle and a "Quadro" link
  back to the board; content column max-w-[960px]; the same
  QueuePanelSection (data, polling and buttons unchanged, incl. Processar
  fila agora).
- Row links: in active and parked rows, the theme title becomes a link to
  `/dashboard/create/<project_id>` when `project_id` is set (accessible name
  "Abrir carrossel: <theme>"); backlog themes (no carousel yet) keep plain
  text.
- Board: `QueuePanelSection` is replaced by a compact one-line chip
  (`QueueSummaryLink`) linking to `/dashboard/queue`: "Fila: N gerando ·
  N na fila · N parada →" (segment "parada" red only when > 0; "Fila vazia"
  when the queue is empty; hidden entirely for non-admins, who get no data).
  It reuses `useGenerationQueue` (acceptable for a chip per the critique).
- i18n additions (PT/EN): `common.sidebar.queue`, `pageTitles.queue`,
  `workflow.queue.openCarousel`, `workflow.queue.summary.*`,
  `workflow.queue.boardLink`.

## Non-Goals

- Board layout/navigation fixes (AE-0568), discovery (AE-0569),
  accessibility (AE-0570).
- New queue backend surface, queue ordering, or the confirm-in-place pattern
  for Descartar/Cancelar (queued as follow-up; Cancelar/Descartar keep their
  existing confirmations from AE-0526).
- Any change to `useGenerationQueue` polling behavior.

## Acceptance Criteria

- [ ] AC1 Given an admin, When they open `/dashboard/queue`, Then the page
  shows the queue title, subtitle, sections (active, dead, backlog) with all
  existing actions incl. Reprocessar and Processar fila agora, and a link
  back to the board.
- [ ] AC2 Given a non-admin, When the dashboard sidebar renders, Then no
  "Fila" item appears; and the queue API stays admin-only (403 latched).
- [ ] AC3 Given an admin on the sidebar, When it renders, Then "Fila" sits
  right after "Workflow Board" and links to `/dashboard/queue`.
- [ ] AC4 Given the board page, When it renders, Then the full queue panel is
  gone and only the compact queue summary chip remains, linking to
  `/dashboard/queue`, with "Fila vazia" when empty and no chip data for
  non-admins.
- [ ] AC5 Given a queue row whose run has a `project_id`, When it renders,
  Then the theme title is a link to that carousel's detail page; given a
  backlog theme without a carousel, Then the title stays plain text.

## Gherkin Scenarios

- `frontend/tests/features/generation-queue-page-ae0557.feature`

## References

- Critique: `/home/pmarins/alter-ego-qa/2026-10-26-board-critique/CRITIQUE.md`
  (P1-5, "Proposed layout: new queue page /dashboard/queue").
- KIMI3 brief AE-0557 section.

## Dev Notes

- Decisions attributed to Pedro (critique follow-up, 2026-10-26).
- No comments in source (JSDoc only); i18n in pt.json + en.json; every
  interactive element gets a `:focus-visible` style.
