# AE-0276 — Responsive data-dense views (calendar, chat, kanban)

Status: Planning
Tier: T2
Priority: Medium
Type: Feature
Area: frontend
Owner: Pedro Marins
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0276-responsive-data-dense
Kanban Card: TBD
Created: 2026-06-24
Updated: 2026-06-24
Parent: AE-0272
Depends-On: AE-0273

## Goal

Make the three data-dense dashboard views usable on mobile: the calendar month grid
scroll-snaps instead of crushing to <50px cells, the chat conversation sidebar becomes a
drawer (reusing AE-0273's primitive), and the kanban migrates its fixed-pixel column
width to a class with scroll-snap.

## Problem

- `calendar-grid.tsx:149` `gridTemplateColumns:"repeat(7,1fr)"` + `minHeight:100` →
  unreadable on phones.
- `chat-sidebar.tsx:32` `width:"280px"` with no collapse; `dashboard-chat-view.tsx`
  flex row → chat area vanishes on narrow screens.
- `neon-kanban-board.tsx:22` `width:"280px"` inline (already scrolls, but inline px
  violates the epic AC#3).

## Scope

- `calendar/calendar-grid.tsx`, `chat/chat-sidebar.tsx`, `chat/dashboard-chat-view.tsx`,
  `board/workflow/components/neon-kanban-board.tsx`.
- **`calendar/calendar-header.tsx:28`** (inline `zIndex:50`, GLM tree-sweep): migrate to a
  class so it does not silently override / collide with the 0273 stacking map
  (hamburger/top-bar at `z-50`). Owns the calendar-area inline-`zIndex` cleanup.

## Non-Goals

- Calendar agenda view (AE-0278 follow-up). Shell drawer infra (AE-0273; reused here).

## Design decisions (from GLM 5.2 review)

- **I4 / N2:** calendar wraps the 7-col grid in `overflow-x-auto` with
  `min-w-[640px]`, `snap-x snap-mandatory`, per-day `snap-start`, and
  `overscroll-behavior-x:contain`. Month view preserved (no info loss).
- **B3 reuse:** chat sidebar becomes a drawer using AE-0273's
  `useOffCanvas`/`useFocusTrap`/`useScrollLock` — NO copy-paste (jscpd/dup gate). Below
  `md`: drawer + toggle, chat full-width. At `md+`: persistent 280px pane.
- **I7:** kanban `width:"280px"` inline → `w-[280px]` class; add `snap-x` +
  `snap-start` columns (N1: low priority polish).

## Acceptance Criteria

- [ ] Calendar: at <640px the month grid scrolls horizontally with snap; each day cell is
      **≥80px wide** (`min-w-[640px]` / 7 ≈ 91px); `overscroll-behavior-x:contain` (no page
      scroll hijack); full 7-col at `md+`.
- [ ] Calendar header inline `zIndex:50` migrated to a class (stacking-map aligned).
- [ ] Chat drawer toggle is a ≥44px touch target on coarse pointers.
- [ ] Chat: below `md` the conversation list is an off-canvas drawer (reusing 0273 hooks)
      with a toggle, chat area full-width; at `md+` the 280px pane is persistent.
- [ ] Chat drawer a11y: focus-trap, Esc, route/selection close, focus-return (inherited
      from 0273 primitive, not reimplemented).
- [ ] Kanban: `width:"280px"` inline → `w-[280px]` class; columns `snap-start`,
      container `snap-x`.
- [ ] Layout-critical inline styles migrated; neon identity unchanged; desktop diff ~nil.
- [ ] Own `.feature` (chat drawer is behavior-changing, AE-0153); gates + lint + typecheck green.
- [ ] No new jscpd duplication (chat drawer reuses 0273 hooks).

## Gherkin Scenarios

```gherkin
Feature: Responsive data-dense dashboard views

  Scenario: Calendar scrolls on mobile without crushing cells
    Given the calendar at 375px
    Then the month grid scrolls horizontally with snap and cells remain legible

  Scenario: Chat sidebar is a drawer on mobile
    Given the chat page at 375px
    Then the conversation list is an off-canvas drawer and the chat area is full width

  Scenario: Selecting a conversation closes the chat drawer
    Given the chat drawer is open on mobile
    When I select a conversation
    Then the drawer closes and focus returns to the toggle

  Scenario: Chat drawer is accessible
    Given the chat drawer is open on mobile
    When I press Escape
    Then the drawer closes and focus returns to the toggle

  Scenario: Chat pane is persistent on desktop
    Given the chat page at 1280px
    Then the 280px conversation pane is always visible with no toggle

  Scenario: Kanban columns snap-scroll on mobile
    Given the workflow board at 375px
    Then columns are fixed width and scroll-snap horizontally
```

## Delta

### MODIFIED
- `calendar-grid.tsx`, `calendar-header.tsx`, `chat-sidebar.tsx`,
  `dashboard-chat-view.tsx`, `neon-kanban-board.tsx` — inline layout/zIndex → Tailwind;
  chat drawer reuses 0273 hooks.
### ADDED
- Data-dense `.feature` (calendar scroll, chat drawer, kanban snap).

## QA Checklist

- [ ] Lint (incl. dup) + typecheck green; tests reference scenarios.
- [ ] 360 / 768 / 1280 — calendar legible+scrolls, chat drawer works, kanban snaps.
</content>
