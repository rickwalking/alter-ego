# AE-0272 — Epic: Responsive dashboard (mobile/tablet adaptation, Tailwind)

Status: In Development
Tier: T3
Priority: High
Type: Epic
Area: frontend
Owner: Pedro Marins
Agent Lane: planner → architect → developer → qa → release
Branch: (per child ticket)
Kanban Card: TBD
Created: 2026-06-24
Updated: 2026-06-24

## Goal

Make the authenticated `/dashboard/*` surface fully usable on mobile and tablet
without losing the "Neon Shell" cyberpunk identity. **Tailwind utilities only** — no
new hand-written `@media` CSS. This is a responsive *adaptation*, not a redesign.

## Problem

Layout-critical styling lives in inline `style={{}}` objects with fixed pixels
(`gridTemplateColumns:"1fr 360px"`, `width:"280px"`, `marginLeft:"240px"`,
`padding:"0 32px"`). Inline styles cannot carry breakpoints, so every layout is frozen
at its desktop value on every viewport. 9 dashboard surfaces are NOT-RESPONSIVE and 4
are PARTIAL (audit in `docs/plans/ae-0272-responsive-dashboard-epic.md`).

## Scope

- All `/dashboard/*` routes and their shared shell (`layout.tsx`, `neon-sidebar.tsx`,
  `neon-top-bar.tsx`) and page components flagged in the audit.
- Convert layout-critical inline `style={{}}` to Tailwind responsive utilities; add an
  off-canvas drawer shell; add a regression gate.

## Non-Goals

- Backend, non-dashboard public/marketing routes, functional redesign, new features.
- Calendar agenda view (filed as AE-0278). Pure responsive adaptation only.

## Children

- **AE-0273** — Responsive app shell + reusable drawer primitive (FOUNDATION; blocks the rest).
- **AE-0274** — Responsive create / carousel flow.
- **AE-0275** — Responsive listing & content pages.
- **AE-0276** — Responsive data-dense views (calendar, chat, kanban).
- **AE-0277** — Responsive-regression gate (CI/tooling).
- **AE-0278** — (follow-up) Calendar `<md` agenda view.

## Acceptance Criteria (epic)

- [ ] Every `/dashboard/*` route is usable, no horizontal overflow, at 360 / 768 / 1024px.
- [ ] Sidebar → accessible off-canvas drawer below `lg`; persistent rail at `lg+`.
- [ ] No layout-critical fixed-pixel `style={{}}` on audited surfaces (enforced by AE-0277).
- [ ] Neon identity preserved (scanlines, grid bg, neon glows, fonts); desktop visual diff ~nil.
- [ ] All children Done; `scripts/ci/gates.sh frontend` + `npm run lint` + typecheck green.

## Plan

`docs/plans/ae-0272-responsive-dashboard-epic.md` (includes external GLM 5.2 review v2).
</content>
