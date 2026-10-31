# AE-0570 — Workflow board accessibility: keyboard navigation, archive overflow menu, archived segmented control

Status: Done
Tier: T2
Priority: High
Type: Feature / UX / Accessibility
Area: Frontend (workflow board)
Owner: Pedro
Agent Lane: developer → qa
Branch: feat/ae-0570-board-accessibility
Kanban Card: TBD
Created: 2026-10-30

## Goal

The desktop workflow board (`/dashboard/workflow`) can be operated from the
keyboard and by a screen reader: one tab stop for the card grid with roving
arrow-key navigation, a per-card overflow menu for archive/restore, and an
Ativos | Arquivados segmented control whose state lives in the URL.

Split PR D of the AE-0557 board rework Pedro ordered after the impeccable
critique (score 18/40; P2-1, P2-2, P2-3 and the "Sam" persona flags). The
layout (AE-0568) and discovery (AE-0569) splits are already merged.

## Problem

- 62 tab stops in column order; no arrow navigation between columns or cards;
  the focus ring is the off-system indigo instead of the documented cyan.
- "New Card" is `<Link><NeonButton/></Link>`, an invalid `a > button` nesting.
- Every card repeats a full-height archive control; the refusal sentence
  repeats on every refused card.
- The Archived/Active toggle is labelled with the destination view, the
  archived view keeps the "Workflow Board" title, and the state is not in the
  URL (Back does not restore it).

## Scope

- P2-2 keyboard: roving tabindex across board cards (one tab stop; Up/Down
  within a column, Left/Right to the same index in the adjacent non-empty
  column clamped, Home/End first/last in the column, Enter opens the card,
  `scrollIntoView({ block: "nearest", inline: "nearest" })` on move). Columns
  are labelled regions whose card lists announce the count.
- Cyan focus ring (`focus-visible:outline-none focus-visible:ring-2
  focus-visible:ring-neon-cyan focus-visible:ring-offset-2
  focus-visible:ring-offset-bg-deep`) on board cards and the new controls.
- Replace the `<Link><NeonButton/></Link>` nesting with a `next/link` styled
  with `neonButtonVariants`; copy "Novo carrossel" / "New carousel".
- P2-3 archived view: segmented control Ativos | Arquivados
  (`role="radiogroup"`, `role="radio"`, `aria-checked`, arrow keys move and
  select), persisted as `?archived=1` (`router.replace`, other params kept);
  in the archive the top bar title reads "Arquivados" / "Archived". The
  "default view is List" part is out of scope (no list view exists yet).
- P2-1 archive controls: per-card overflow button (`⋯`, 28px, top-right,
  outside the card link, `aria-label="Mais ações: <title>"` / "More actions:
  <title>") opening a menu (`role="menu"`): "Arquivar" (keeping the existing
  confirm step inside the menu) or "Restaurar" on the archived board, or the
  refusal reason as disabled menu text; nothing at all for
  `archiveRefusal === "published"` or when `canArchive` is false. The refusal
  sentence no longer repeats on every card. Escape closes the menu and returns
  focus to the trigger; the menu is `position: fixed` so the column's
  `overflow-y-auto` cannot clip it; an outside mousedown closes it.
- pt/en strings for every new label; `:focus-visible` style on every new
  interactive element.

## Non-Goals

- List view default for the archive (no list view exists).
- Queue page move (AE-0557, another lane).
- Detail-page prev/next and breadcrumb href (AE-0568 shipped the scroll and
  sequence persistence; prev/next wiring stays as-is).
- Changing the archive confirm from an inline step to a modal dialog (the
  confirm stays inside the menu per Pedro's brief).

## Acceptance Criteria

- [ ] AC1 Given the board, When I press Tab, Then exactly one card link is in
      the tab order (the first card of the first non-empty column by default)
      and arrow keys move a cyan focus ring: Up/Down within the column
      (clamped), Left/Right to the same index in the adjacent non-empty column
      (clamped), Home/End to the first/last card of the column; Enter opens
      the focused card.
- [ ] AC2 Given a column, Then it is a labelled region (`section
      aria-labelledby`) whose card list announces its item count.
- [ ] AC3 Given the top bar, Then "Novo carrossel" / "New carousel" is a
      single link styled as a button (no `a > button` nesting).
- [ ] AC4 Given the top bar, Then an Ativos | Arquivados segmented control
      (`radiogroup`, `aria-checked`, arrow keys) switches the board, persists
      the choice as `?archived=1` while keeping the other query params, and
      makes the top bar title "Arquivados" / "Archived" in the archive.
- [ ] AC5 Given a card I may archive, Then a `⋯` overflow button labelled
      "Mais ações: <title>" / "More actions: <title>" opens a fixed-position
      menu with "Arquivar" followed by the existing confirm step, and Escape
      closes the menu returning focus to the trigger.
- [ ] AC6 Given a card with a refusal reason, Then the reason shows once,
      disabled, inside that card's open menu (not repeated on the card); given
      a published card or one I may not archive, Then no control renders.
- [ ] AC7 Given the archived board, Then each card's menu offers "Restaurar",
      and a failed archive or restore shows the failure in the card's menu.

## Gherkin Scenarios

- `frontend/tests/features/board-accessibility-ae0570.feature`

## References

- Critique: `/home/pmarins/alter-ego-qa/2026-10-26-board-critique/CRITIQUE.md`
  (P2-1, P2-2, P2-3, "Sam" persona flags).
- Split PR D of the AE-0557 board critique implementation order.
- Files: `page.tsx`, new `workflow-board-chrome.tsx`,
  `workflow-view-switch.tsx`, `card-archive-action.tsx`,
  `workflow-board-column.tsx`, `neon-kanban-board.tsx`,
  `use-board-roving-focus.ts`, `components/types.ts`, `types.ts`,
  `constants/workflow.ts`, `i18n/locales/{pt,en}.json`.

## Dev Notes

- Decisions attributed to Pedro (critique follow-up, 2026-10-26; copy "Novo
  carrossel" / "New carousel" per his brief).
- No comments in source (JSDoc/docstrings only); types colocated in
  `types.ts` under `src/modules/**`; every interactive element gets a
  `:focus-visible` style; i18n keys in pt and en.
- The menu uses `position: fixed` (not the clipping `NeonDropdown` absolute
  positioning) and manages Escape/outside-click/focus-return itself because
  `NeonDropdown` has no keyboard support.

## Final Summary

Merged to `main` in PR #307 (86c8871f, 2026-10-30). Closed on 2026-10-31 (ticket housekeeping, no code change).
