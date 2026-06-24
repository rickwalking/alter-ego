# AE-0272 — Responsive Dashboard Epic (impeccable `adapt`)

**Goal:** Make the authenticated `/dashboard/*` surface fully mobile/tablet friendly
without losing the "Neon Shell" cyberpunk identity. **Tailwind utilities only** — no
new hand-written `@media` CSS, no pure-CSS responsive hacks. Identity preservation
(DESIGN.md) is a hard constraint; this is a *responsive adaptation*, not a redesign.

## Why the dashboard is not responsive (root cause)

Layout-critical styling lives in inline `style={{}}` objects with **fixed pixel
values** (`gridTemplateColumns: "1fr 360px"`, `width: "280px"`, `marginLeft: "240px"`,
`padding: "0 32px"`). Inline styles **cannot express breakpoints** — there is no
`md:` inside a `style` object. So every fixed-pixel layout decision is frozen at the
desktop value on every viewport.

**The fix is structural, not cosmetic:** move *layout-determining* declarations
(`display`, `grid-template-columns`, `width`, `flex-direction`, layout `padding`,
`margin-left`) out of `style={{}}` and into Tailwind responsive utility classes.
Color/border/shadow/token inline styles may stay (they are not viewport-dependent) —
we only migrate what must respond. This keeps diffs tight and identity intact.

## Audit summary (13 affected surfaces)

NOT-RESPONSIVE (9): dashboard layout shell (sidebar + content margin), dashboard
overview, calendar grid, chat sidebar, create form, create workspace, publish page,
workflow kanban, create-progress-steps.
PARTIAL (4): analytics charts, blog-posts (grid + search width), personas (grid +
search width), palettes grid.

## Breakpoint strategy (documented, consistent)

Tailwind v4 defaults. One shell breakpoint, content-driven elsewhere.

| Concern | Mobile (base) | `md` 768px | `lg` 1024px |
|---|---|---|---|
| **App shell sidebar** | off-canvas drawer + hamburger | drawer | persistent 240px rail |
| Content margin-left | `ml-0` | `ml-0` | `lg:ml-[240px]` |
| Two-pane layouts (create workspace, chat) | stacked, 1 col | stacked | side-by-side |
| Card grids | 1 col | 2 col | 3+ col / `auto-fill` |
| Calendar month grid | horizontal-scroll wrapper (`min-w`+`overflow-x-auto`) | scroll | full 7-col |
| Kanban | scroll-snap columns | scroll | scroll |
| Layout padding | `p-4` | `md:p-6` | `lg:p-7` / `px-4 md:px-8` topbar |

Touch targets ≥44px on coarse pointers. All motion behind `prefers-reduced-motion`
(reuse existing global guard). No content hidden on mobile — everything reachable.

## Wave breakdown (tickets)

- **AE-0272** (epic parent) — this doc.
- **AE-0273 — Responsive app shell (FOUNDATION).** `dashboard/layout.tsx`,
  `neon-sidebar.tsx`, `neon-top-bar.tsx`. Off-canvas sidebar drawer with hamburger
  toggle + backdrop + close-on-navigate; content `ml` responsive; top-bar padding
  responsive; title truncation. New small client state for drawer open/close (UI
  state, not data — `useState` in the already-client layout). Ships first; every
  other ticket builds on the freed horizontal space.
- **AE-0274 — Responsive create / carousel flow.** `create/page.tsx`,
  `create/[id]/page.tsx`, `create/[id]/publish/page.tsx`, `create-progress-steps.tsx`,
  `create-sidebar.tsx`. `1fr 360px` grids → `grid-cols-1 lg:grid-cols-[1fr_360px]`;
  progress steps horizontally scroll / wrap on mobile; publish `maxWidth` container
  → `max-w-[960px] w-full` + header `flex-col sm:flex-row`; responsive padding.
- **AE-0275 — Responsive listing & content pages.** `dashboard/page.tsx` (quick
  actions 3-col → `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`, activity `1fr 1fr` →
  `grid-cols-1 lg:grid-cols-2`), `blog-posts/page.tsx` + `blog-posts-grid.tsx`
  (search `w-[200px]` → `w-full sm:w-[200px]`, featured/regular `1fr 1fr` →
  responsive), `personas/page.tsx` (search width, `minmax(340px…)` → `minmax(260px…)`),
  palettes grid (`minmax(260px…)` → `minmax(220px…)`), `analytics` velocity-chart
  overflow guard.
- **AE-0276 — Responsive data-dense views.** `calendar/calendar-grid.tsx` (7-col
  wrapped in `overflow-x-auto` with `min-w-[680px]`, smaller cells on mobile; keep
  month view, no info loss), `chat/chat-sidebar.tsx` + `dashboard-chat-view.tsx`
  (280px sidebar → drawer/toggle on mobile, full-width chat), `neon-kanban-board.tsx`
  (scroll-snap, `w-[280px]` columns kept but `snap-x` + `scroll-pl`).

Dependency: AE-0273 first (foundation). AE-0274/0275/0276 are independent of each
other and can run in parallel after 0273.

## Conversion technique (reference patterns)

```tsx
// BEFORE — frozen desktop layout
<div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: "24px" }}>

// AFTER — Tailwind responsive (arbitrary value for the fixed track is fine; matches
// existing w-[200px] convention in the repo)
<div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
```

```tsx
// Shell sidebar — drawer below lg, rail at lg+
<aside className={cn(
  "fixed inset-y-0 left-0 z-40 w-[240px] transition-transform duration-200 ease-out",
  "lg:translate-x-0",
  open ? "translate-x-0" : "-translate-x-full",
)} style={{ background: BG_SIDEBAR, /* identity styles stay */ }}>
```

```tsx
// Content wrapper margin
<div className="flex flex-1 flex-col lg:ml-[240px]">
```

Use `cn()` (already in repo) for conditional classes. `minmax(0,1fr)` not bare `1fr`
to prevent grid blowout from long content. Keep all neon color/border/shadow inline
styles or tokens untouched.

## Acceptance criteria (epic-level)

1. Every `/dashboard/*` route is usable and free of horizontal overflow at 360px,
   768px, and 1024px widths (verified via Playwright mobile viewport screenshots).
2. Sidebar collapses to an accessible drawer (hamburger, `aria-expanded`, focus
   handling, Esc to close, backdrop click to close) below `lg`; persistent rail at `lg+`.
3. No layout-critical fixed-pixel `style={{}}` remains on the audited surfaces —
   replaced by Tailwind responsive utilities. (Enforced per-ticket by review + a
   lightweight grep check listed in each ticket's QA checklist.)
4. Neon identity preserved: scanlines, grid bg, neon borders/glows, fonts unchanged.
   Visual diff at desktop width is ~nil (pure additive breakpoints).
5. Touch targets ≥44px on coarse pointers for primary nav/actions.
6. All existing tests pass; new component tests cover the drawer open/close and the
   responsive class application. `.feature` scenarios for behavior-changing shell nav.
7. `scripts/ci/gates.sh frontend` green; `npm run lint` (incl. boundaries, dup,
   component-types) green; typecheck green.

## Out of scope

Backend, non-dashboard marketing/landing routes, functional redesign, new features.
Pure responsive adaptation only.

---

## v2 — External architect revisions (opencode GLM 5.2, APPROVE-WITH-CHANGES)

A grounded skeptical review (read the real files) found 3 blockers + 9 improvements.
All accepted. These supersede the v1 sections above where they conflict.

### Resolved blockers

- **B1 — Shell trigger mechanism (layout↔page state flow).** `NeonTopBar` is rendered
  by all 11 dashboard pages, not the layout. **Decision:** the hamburger is a
  **layout-level sticky button** (`fixed top-0 left-0 z-50 lg:hidden`), NOT a TopBar
  prop — keeps the shared `NeonTopBar` organism presentational. `NeonTopBar` gets only
  responsive left padding (`pl-14 lg:pl-8`) so its title clears the hamburger. Drawer
  `open` state stays in the already-client `layout.tsx`.
- **B2 — Inline `zIndex` beats Tailwind z-classes (specificity).** `neon-sidebar.tsx:50`
  and `neon-top-bar.tsx:32` set `zIndex:30` inline, which would kill the drawer's `z-40`
  class. **Decision:** add `zIndex` to the migrate-to-Tailwind list. **Stacking map
  (documented):** backdrop `z-30`, drawer `z-40`, sticky top-bar + hamburger `z-50`. At
  `lg+` the backdrop does not render.
- **B3 — Extract a reusable drawer primitive in 0273 (jscpd/dup-gate risk).** AE-0276's
  chat sidebar is a *second* off-canvas drawer; hardcoding trap/lock/Esc into the
  sidebar would be copy-pasted by 0276 and fail the `lint:dup` gate (AE-0149).
  **Decision:** 0273 ships a hand-rolled (no new dep) reusable primitive —
  `useOffCanvas` (disclosure + Esc + route-change close via `usePathname`) plus
  `useFocusTrap` and `useScrollLock` (`overflow:hidden` + `overscroll-behavior:contain`
  on body). 0276's chat drawer **reuses** them. Focus-return to the trigger on close.

### Adopted improvements

- **I1 — `minmax(0,1fr)` everywhere** (not bare `1fr`) for the two-pane grids
  (create `page.tsx:77`, `create/[id]:28`, publish). Prevents input/text blowout.
- **I2 — Single-source the sidebar width.** Define `--sidebar-width: 240px` once
  (globals `@theme`/`:root`, mirroring `SIDEBAR_WIDTH_PX`) and use
  `w-[var(--sidebar-width)]` / `lg:ml-[var(--sidebar-width)]`. No magic `240`.
- **I3 — Decouple two-pane breakpoint from the shell breakpoint.** Two-pane content
  (create workspace, chat) goes side-by-side at **`md` (768px)**, not `lg` — at 768px the
  shell is already a drawer so content owns the full width. Shell rail stays `lg`.
- **I4 — Calendar: horizontal-scroll + `snap-x snap-mandatory` + per-day snap +
  `overscroll-behavior-x: contain`**, `min-w-[640px]` (N2). File **AE-0278 follow-up**
  for a true `<md` agenda view (out of scope here; not the permanent excuse).
- **I5 — Enforce via a real gate, not a grep (own ticket AE-0277).** A
  `scripts/check-responsive-dashboard.mjs` checker scoped to the audited dashboard
  files that fails on reintroduced layout-freezing inline props
  (`gridTemplateColumns`, px `marginLeft`, fixed px `width` on layout containers,
  `display:"grid"/"flex"` with no class), wired into `npm run lint` + `gates.sh`, with a
  **rule-fires seeded-violation test** (AE-0180). CI/tooling ticket (unit-test path,
  AE-0153).
- **I6 — Touch targets ≥44px (0273 AC).** Sidebar nav `Link` padding (~36px) and logout
  button (28×28) are sub-44px. Migrate to classes; mobile `min-h-11`/`py-3`, `lg:py-2.5`
  to preserve desktop density.
- **I7 — Kanban `width:"280px"` inline → `w-[280px]` class** (0276) — no AC#3 exception.
- **I8 — AE-0276 chat drawer is behavior-changing → its own `.feature`** (AE-0153) with
  focus-trap/route-close/Esc scenarios. 0273 shell nav likewise.
- **I9 — `NeonTopBar` mobile reflow (0273):** `min-w-0` + `truncate` title, breadcrumb
  hidden `<sm` (`hidden sm:flex`), `actions` allowed to wrap.
- **N4 — `create-progress-steps.tsx:48` `overflow:"hidden"` inline → `overflow-x-auto`**
  responsively (0274), so steps scroll on mobile instead of clipping.

### Revised wave list

- **AE-0272** epic (this doc).
- **AE-0273 — Responsive app shell + reusable drawer primitive (FOUNDATION).** Layout-level
  hamburger, off-canvas drawer, `useOffCanvas`/`useFocusTrap`/`useScrollLock`, stacking
  map, `--sidebar-width` var, touch targets, `NeonTopBar` reflow. Blocks 0274/0275/0276.
- **AE-0274 — Responsive create / carousel flow.** `minmax(0,1fr)` two-panes at `md`,
  progress-steps `overflow-x-auto`, publish container + header reflow.
- **AE-0275 — Responsive listing & content pages.** Overview, blog-posts, personas,
  palettes, analytics grids + search widths.
- **AE-0276 — Responsive data-dense views.** Calendar snap-scroll, chat drawer (reuses
  0273 primitive), kanban `w-[280px]` class + snap. Own `.feature`.
- **AE-0277 — Responsive-regression gate.** `check-responsive-dashboard.mjs` +
  rule-fires test, wired into lint/gates. CI/tooling.
- **AE-0278 — (follow-up, filed not built)** Calendar `<md` agenda view.

### QA note (N3)

Migrating inline `zIndex:30`→`z-40`/`z-50` is an invisible desktop stacking change; AC#4
"visual diff ~nil" explicitly accepts stacking-order micro-changes — QA should not flag.
</content>
