# AE-0568 — Workflow board fits the screen and keeps the user's place

Status: In Development
Tier: T2
Priority: High
Type: Bug / UX
Area: Frontend (workflow board)
Owner: Pedro
Agent Lane: developer → qa
Branch: feat/ae-0568-board-layout
Kanban Card: TBD
Created: 2026-10-27
Updated: 2026-10-28

## Goal

The desktop workflow board (`/dashboard/workflow`) fits one viewport: columns
scroll independently inside a fixed-height board, empty and done columns
collapse to rails, the breadcrumb actually links back, the board scroll
survives a round trip into a carousel, and the carousel workspace marks
"Workflow Board" active in the sidebar. This is split PR A (the P0 layout and
navigation findings) of the AE-0557 board rework ordered by Pedro after the
impeccable critique (score 18/40).

## Problem

- The board is one horizontal scroller: 37 cards make a 3,319px tall element
  whose scrollbar sits ~2,600px below the fold; 32 of 37 cards are off-screen
  at load on 1440x900 and the two columns that matter most (Final review,
  Published) are the farthest away.
- Opening a carousel and pressing Back remounts the board at the far left and
  top; the detail page's breadcrumb passes `href` but `NeonBreadcrumb` never
  renders it, and no sidebar item is active on `/dashboard/create/<id>`.

## Scope

- `NeonKanbanBoard`: fixed board height (`100dvh` minus the 56px top bar and
  page padding) with `overflow-x-auto overflow-y-hidden`; each column becomes
  `flex flex-col min-h-0` with its own `overflow-y-auto` card list; open
  columns use `flex-1 basis-0` between 232px and 320px; drop `snap-x`/`snap-start`
  and the `minHeight` style.
- Empty columns and the done columns (Published, Rejected) collapse to a 44px
  vertical rail (rotated header, count, `title`, keyboard-focusable button)
  that expands on click; the expanded set persists in
  `localStorage("workflow-board:expanded")`; an expanded empty column shows the
  existing `workflow.board.noProjects` text.
- Column semantics: each column is a `<section aria-labelledby>` with a heading
  and the card list is a `role="list"` of `role="listitem"` cards.
- `NeonBreadcrumb`: items with `href` render as `next/link` links (mono style,
  muted hover, cyan focus ring); the last item stays plain text.
- Board scroll restore: before a card navigation the board's `scrollLeft` and
  each column's `scrollTop` are saved to `sessionStorage("workflow-board:scroll")`
  and restored once after the first board load lands.
- Sidebar: `/dashboard/create/<id>` (but not `/dashboard/create` itself) marks
  the Workflow Board item active via an explicit `isActiveItem` match.
- Card navigation stores the ordered ids and localized name of its column in
  `sessionStorage("workflow-board:sequence")`. The carousel workspace renders
  previous/next controls with the current position and supports `[` and `]`
  outside editable fields.

## Non-Goals

- Search, filters, sort, list view and URL state (split PR B, AE-0569).
- Moving the queue panel to its own page (split PR C, AE-0557).
- Roving-tabindex keyboard navigation, the archive overflow menu and the segmented
  Ativos/Arquivados control (split PR D, AE-0570).
- Semantic status badge colors and card content fixes (split PR B, AE-0569).
- Any backend change.

## Acceptance Criteria

- [ ] AC1 Given a board with more cards than fit the viewport, When it renders,
  Then the board area is height-constrained (no vertical page scroll) and each
  column's card list scrolls independently while its header stays visible.
- [ ] AC2 Given empty or done columns (Published, Rejected), When the board
  renders, Then they appear as vertical rails with the count, and clicking a
  rail expands it into a normal column; expanded columns persist across
  reloads in localStorage.
- [ ] AC3 Given a column, Then it is announced as a labelled section with a
  list of items, and an expanded empty column shows "Nenhum projeto".
- [ ] AC4 Given a page that passes a breadcrumb item with `href`, When it
  renders, Then that item is a real link with a visible focus style; the last
  item is not a link.
- [ ] AC5 Given the board scrolled to a card, When the card is opened and the
  user comes Back, Then the board's horizontal position and the column scroll
  positions are restored once after the first board load.
- [ ] AC6 Given `/dashboard/create/<id>`, When the sidebar renders, Then
  "Workflow Board" is active; given `/dashboard/create` itself, Then it is not.
- [ ] AC7 Given a card opened from a board column, When the carousel workspace
  renders, Then previous/next controls follow that column's ordered ids, show
  the current position, and respond to bracket shortcuts outside editable fields.

## Gherkin Scenarios

- `frontend/tests/features/board-layout-ae0568.feature`

## References

- Critique: `/home/pmarins/alter-ego-qa/2026-10-26-board-critique/CRITIQUE.md` (P0-1, P0-2, P1-3 roles, P3 empty-column text)
- Files: `neon-kanban-board.tsx` + `components/types.ts`, `workflow/page.tsx`,
  `neon-breadcrumb.tsx`, `neon-sidebar-parts.tsx`.

## Dev Notes

- Decisions attributed to Pedro (critique follow-up, 2026-10-26).
- i18n: add `workflow.board.expandColumn` (PT/EN); reuse `workflow.board.noProjects`.
- No comments in source (JSDoc/docstrings only); types colocated in `types.ts`;
  every interactive element gets a `:focus-visible` style.
