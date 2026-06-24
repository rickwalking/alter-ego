# AE-0273 — Responsive app shell + reusable off-canvas drawer primitive

Status: Dev Complete
Tier: T2
Priority: High
Type: Feature
Area: frontend
Owner: Pedro Marins
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0273-responsive-app-shell
Kanban Card: TBD
Created: 2026-06-24
Updated: 2026-06-24
Parent: AE-0272

## Goal

Turn the fixed 240px dashboard sidebar into an accessible off-canvas drawer below `lg`,
persistent rail at `lg+`, driven by a layout-level hamburger. Ship a reusable drawer
primitive (hooks) that AE-0276's chat drawer will reuse. Foundation for the epic.

## Problem

`dashboard/layout.tsx` hardcodes `marginLeft: 240px`; `neon-sidebar.tsx` is `fixed`
240px with no mobile collapse; `neon-top-bar.tsx` has fixed `padding:"0 32px"` and inline
`zIndex:30`. On phones the sidebar overlays content and there is no way to reach nav.

## Scope

- `frontend/src/app/dashboard/layout.tsx`, `neon-sidebar.tsx`, `neon-top-bar.tsx`.
- New hooks: `useOffCanvas` (disclosure + Esc + route-change close via `usePathname`),
  `useFocusTrap`, `useScrollLock` (`overflow:hidden` + `overscroll-behavior:contain`).
- `--sidebar-width: 240px` CSS var (mirrors `SIDEBAR_WIDTH_PX`).

## Non-Goals

- Page content grids (AE-0274/0275). Chat drawer itself (AE-0276, reuses these hooks).

## Design decisions (from GLM 5.2 review)

- **B1:** hamburger is a **layout-level `fixed` button** (`fixed top-0 left-0 z-50
  lg:hidden` — always-visible trigger, not `sticky`), not a `NeonTopBar` prop.
  `NeonTopBar` keeps presentational; gets `pl-14 lg:pl-8` so the title clears the
  hamburger. `open` state in `layout.tsx`.
- **Hooks are presentation-agnostic:** drawer side/width/classes are passed by the
  consumer (not baked in), so AE-0276's chat drawer reuses them without a fork.
- **B2 / stacking map:** migrate inline `zIndex` to classes. Backdrop `z-30`, drawer
  `z-40`, sticky top-bar + hamburger `z-50`. Backdrop does not render at `lg+`.
- **B3:** hand-rolled reusable primitive (no new dep). Focus-trap, focus-return to
  trigger on close, Esc, route-change close, scroll-lock.

## Acceptance Criteria

- [ ] Below `lg`: sidebar is translated off-canvas (`-translate-x-full`), slides in on
      hamburger (`translate-x-0`), backdrop (`z-30`, `lg:hidden`) closes on click.
- [ ] At `lg+`: sidebar is a persistent rail (`lg:translate-x-0`), no hamburger, no
      backdrop; content uses `lg:ml-[var(--sidebar-width)]` (else `ml-0`).
- [ ] Drawer a11y: focus moves into drawer on open and is trapped; Esc closes; focus
      returns to the hamburger on close; body scroll locked while open
      (`overscroll-behavior:contain`); drawer closes on route change.
- [ ] Hamburger has `aria-label`, `aria-expanded`, `aria-controls` → sidebar `id`.
- [ ] `--sidebar-width` defined once; no literal `240` in shell class strings; a unit test
      asserts `--sidebar-width` equals JS `SIDEBAR_WIDTH_PX` (no drift between the two).
- [ ] Inline `zIndex` removed from `neon-sidebar.tsx` / `neon-top-bar.tsx`; stacking map
      applied via classes.
- [ ] **Touch targets ≥44px** (I6): sidebar nav `Link` → `min-h-11 py-3 lg:py-2.5`;
      logout button ≥44px on coarse pointers.
- [ ] **NeonTopBar reflow** (I9): title `min-w-0 truncate`; breadcrumb `hidden sm:flex`;
      `actions` may wrap; padding `px-4 md:px-8` (replaces `0 32px`); `pl-14 lg:pl-8`.
- [ ] Neon identity unchanged (border/bg/glow inline styles preserved); desktop visual
      diff ~nil (stacking micro-change accepted per epic N3).
- [ ] Hooks reusable + unit-tested; `.feature` for shell nav; `gates.sh frontend` green.

## Gherkin Scenarios

```gherkin
Feature: Responsive dashboard app shell

  Scenario: Sidebar is a drawer on mobile
    Given the dashboard is viewed at 375px width
    Then the sidebar is hidden off-canvas and a menu button is visible

  Scenario: Opening the drawer traps focus and locks scroll
    Given the dashboard at 375px
    When I activate the menu button
    Then the sidebar slides in, focus moves into it, and body scroll is locked

  Scenario: Escape and route-change close the drawer
    Given the drawer is open on mobile
    When I press Escape or navigate to another dashboard route
    Then the drawer closes and focus returns to the menu button

  Scenario: Backdrop click closes the drawer
    Given the drawer is open on mobile
    When I click the backdrop outside the drawer
    Then the drawer closes and focus returns to the menu button

  Scenario: Persistent rail on desktop
    Given the dashboard at 1280px width
    Then the sidebar is a persistent rail, no menu button, and content is offset by the sidebar width
```

## Delta

### ADDED
- `useOffCanvas`, `useFocusTrap`, `useScrollLock` hooks (+ tests); layout hamburger +
  backdrop; `--sidebar-width` token; shell `.feature`.
### MODIFIED
- `dashboard/layout.tsx`, `neon-sidebar.tsx`, `neon-top-bar.tsx` (inline layout styles →
  Tailwind responsive classes; zIndex migrated; touch targets; topbar reflow).
### REMOVED
- Inline `marginLeft:240`, `zIndex:30`, fixed topbar padding.

## QA Checklist

- [x] `npm run lint` (boundaries/dup/component-types/i18n) + `npm run typecheck` green.
- [x] Vitest covers hooks (open/close/Esc/trap/lock) and drawer class application.
- [ ] Playwright/manual: 360 / 768 / 1024 / 1280 — no horizontal overflow; drawer a11y.
- [x] No new jscpd duplication; hooks are the single source for off-canvas behavior.

## Progress Log

- 2026-06-24 — Implemented reusable hooks (`useOffCanvas`/`useFocusTrap`/`useScrollLock`),
  layout hamburger + backdrop, sidebar drawer classes (`w-[var(--sidebar-width)]`,
  off-canvas translate, `lg` rail), `--sidebar-width` token, touch targets
  (`[@media(pointer:coarse)]:min-h-11`), NeonTopBar reflow, inline `zIndex`→`z-*` classes.
  All frontend gates reproduced green.

## Test Evidence

```
GATES_JSON (frontend full run): pass across lint, lint-changed, component-types,
duplication, dead-code, typecheck, build, legacy-guard, legacy-inventory, security,
integrity, test (102 files / 936 tests passed), schema-drift, duplication-tests, format.
Only initial FAIL was frontend:format (3 files) → fixed via prettier --write → PASS.
```

- New unit suites: `use-off-canvas.test.ts` (5), `use-focus-trap.test.tsx` (5),
  `use-scroll-lock.test.ts` (4), `sidebar-width-token.test.ts` (1), extended
  `neon-sidebar.test.tsx` (drawer translate classes / id / aria). Total 936 FE tests pass.
- `bash scripts/ci/check-integrity.sh frontend` → 0 net-new blockers.
</content>
