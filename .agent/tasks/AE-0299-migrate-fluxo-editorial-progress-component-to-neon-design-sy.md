# AE-0299 — migrate fluxo editorial progress component to neon design system

Status: Ready
Tier: T1
Priority: Medium
Type: Refactor
Area: frontend
Owner: Unassigned
Branch: TBD
Created: 2026-07-01
Updated: 2026-07-01

## Goal

The "Fluxo Editorial" progress panel in the Create Carousel page matches the redesigned Neon
design system used by its siblings, instead of rendering with stale legacy tokens (purple accent,
undefined text color).

## Problem

On the Create Carousel page (`frontend/src/app/dashboard/create/[id]/page.tsx`, middle column of
the 2-col grid at line 209), the "PROCESSANDO ATUALMENTE / Gerando imagens" card, its progress
bar, per-slide list and vertical phase checklist still use **legacy shadcn tokens** while the
surrounding page was migrated to the Neon system by AE-0284 (`ed7b9f46`, `6d73c8bf`). Those
commits restyled the siblings (`create-progress-steps.tsx`, `create-workspace-sidebar.tsx`,
`project-summary-card.tsx`, `create-workflow-artifacts.tsx`, `create-workflow-panel.tsx`, added
`workflow-status-badge.tsx`) but touched **none** of the progress sub-tree.

Outdated files (all under `frontend/src/app/dashboard/create/workspace/`):
- `create-workflow-progress.tsx` (adapter → `CarouselProgress`)
- `create-carousel-progress.tsx` (the "PROCESSANDO ATUALMENTE" card + stalled timer + checklist)
- `phase-item.tsx` (each checklist row)
- `phase-progress-detail.tsx` (label + "Generating N slide images in parallel" bar)
- `slide-progress-grid.tsx` (the Slide 1..N list)
- `progress-icons.tsx` (spinner / check / status icons)

Two hard proofs the tokens are stale, not a valid alternate theme:
- **`--color-primary` is purple, not cyan.** `globals.css:97` resolves it to
  `--color-primary-500 = oklch(0.62 0.214 278)` (violet). The redesigned page accent is neon cyan
  `#00d4ff` (`--color-neon-cyan`, globals.css:50). So the spinner, active-phase dot, progress-bar
  fill and check badges render **purple**, clashing with the cyan page
  (`create-carousel-progress.tsx:101,144`, `phase-item.tsx:31-34,52`,
  `phase-progress-detail.tsx:62`, `progress-icons.tsx:71,98`).
- **`--color-text` is undefined** — `grep -- "--color-text:" globals.css` returns nothing (only
  `--color-text-primary/muted/dim` exist). Every `text-[var(--color-text)]`
  (`phase-item.tsx:52`, `phase-progress-detail.tsx:42`, `slide-progress-grid.tsx:40`,
  `progress-icons.tsx:98`) renders with no color (inherits) — a dangling legacy token.

Minor corroborating smell: `slide-progress-grid.tsx:41` hardcodes `Slide {slide.number}` with no
i18n, unlike the migrated siblings.

## Prior Refinement Decisions Carried (do NOT re-derive)

This migration carries already-ratified decisions; it invents no new styling. Plan:
`.agent/reports/AE-0299.arch-plan.md`.

- **Semantic status-badge map = AE-0284 (user-approved).** Route every rendered status through
  `resolveWorkflowStatusVisual` (`workspace/workflow-status.ts`) + `WorkflowStatusBadge` — not a
  hand-styled span. Locked: `in_progress` = cyan **pulse dot**; `awaiting_human` = magenta;
  **readyToPublish = teal (NOT green)**; published/completed = green; rejected/failed = red; status
  conveyed by **label + colour + dot, never colour alone**.
- **A11y (AE-0284 MUST).** Pulse dot `animate-pulse motion-reduce:animate-none`; label-override
  badges compose `aria-label` = `"<label>, <status>"`; `role="status"` (polite) ONLY on the badge
  that *is* the status.
- **Responsive (AE-0272..0277, gated by `lint:responsive-dashboard`).** Tailwind utilities only; no
  hand `@media`; no layout-critical inline `style`; two-pane grids `md:grid-cols-[minmax(0,1fr)_360px]`;
  touch targets ≥44px; no horizontal overflow at 360/768/1024px; neon identity preserved.
- **Token map** = AE-0299 §Scope + `frontend/src/constants/neon.ts` (`NEON_CYAN`, `BG_CARD`,
  `NEON_CARD_BORDER`, `TEXT`/`--color-text-primary`), primitives `NeonBadge` / `NeonAlert`.
- **i18n** — reuse existing `create.status.*` labels (en.json:310-320); no `text-transform` on the
  raw enum.

## Scope

- Migrate the six files above off raw shadcn tokens onto the Neon system used by the restyled
  siblings:
  - `var(--color-primary)` → neon cyan (`text-neon-cyan` / `NEON_CYAN` / `var(--color-neon-cyan)`).
  - `var(--color-background)` / `var(--color-bg-card)` + `var(--color-border)` → `BG_CARD` /
    `NEON_CARD_BORDER` (as the panel wrapper and sidebar do).
  - undefined `var(--color-text)` → `var(--color-text-primary)` / `text-text-primary`; keep the
    defined `--color-text-muted`.
  - the ad-hoc `destructive`/`warning` callouts → Neon equivalents (`NeonAlert` / `NeonBadge`
    variants), matching `create-workflow-panel.tsx` and `workflow-status-badge.tsx`.
- Reference "new" pattern: `workflow-status-badge.tsx`, `create-workflow-artifacts.tsx`,
  `create-progress-steps.tsx`, `create-workspace-sidebar.tsx`.
- Fix the `slide-progress-grid.tsx` hardcoded "Slide" label via i18n (en + pt) while in the file.

## Non-Goals

- No change to progress **behavior/logic** — phase computation, stalled-timer, slide counts, and
  the data contract stay identical. This is a visual-token migration only.
- Do not restyle already-migrated siblings.
- No new design tokens; only adopt existing Neon constants (`@/constants/neon`) / primitives
  (`@/components/atoms/neon-badge`, `NeonAlert`).

## Behavior-Change Classification (AE-0153)

Pure visual-token refactor — **no public/user-visible behavior change** (logic, data flow, and
DOM structure/semantics unchanged; only color/token classes swap). Per AE-0153 this substitutes
focused unit/snapshot tests plus **visual verification** (AE-0282 visual-verification ratchet) in
lieu of a `.feature` file. Affected gate: `frontend:lint` (Tailwind theme tree-shake / token
lint, AE-0279). QA to sign off on the no-`.feature` classification.

## Acceptance Criteria

- [ ] None of the six files reference `var(--color-primary)` or the undefined `var(--color-text)`;
      accents render neon cyan and text uses a defined token.
- [ ] The progress panel visually matches the Neon siblings (card border, background, badge/alert
      styles), confirmed by a before/after screenshot in Test Evidence (AE-0282).
- [ ] Progress logic is unchanged — existing unit/snapshot tests for the progress components pass
      without assertion changes to behavior (only token/class snapshot updates).
- [ ] The "Slide N" label is i18n-driven in both `en` and `pt` (no hardcoded copy).
- [ ] `frontend:lint` (incl. Tailwind theme tree-shake) and typecheck pass.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

Files (all `frontend/src/app/dashboard/create/workspace/`):
- `create-workflow-progress.tsx`, `create-carousel-progress.tsx`, `phase-item.tsx`,
  `phase-progress-detail.tsx`, `slide-progress-grid.tsx`, `progress-icons.tsx`
- `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt.json`

## Dependencies

- Related: AE-0284 (semantic v2 status badge / Neon migration of the create-carousel siblings),
  AE-0282 (visual verification), AE-0279 (Tailwind theme lint gate).

## Decision Log

### 2026-07-01 — architect + external review (GLM 5.2)

Plan `.agent/reports/AE-0299.arch-plan.md`; review `.agent/reports/AE-0295-0299.skeptical-review.md`
(converged, no blockers). Carries prior refinements (AE-0284 status map, AE-0272..0277 responsive,
AE-0282 visual verification) — invents no new styling. Hardened:
- **Status domain is the carousel *workflow* enum** (distinct from AE-0295/0296 blog status — do not
  conflate). Enforce **structurally**: `Record<WorkflowStatus,…>` (compile-time) + the runtime
  unknown branch **throws in dev/test** (cyan only as last-resort prod guard).
- **A11y test:** exactly one `role="status"` live region; pulse dot honors `motion-reduce`.
- Visual verification at 360/768/1024; `frontend:lint` (theme tree-shake + responsive gate).

## Progress Log

### 2026-07-01

Ticket created from production troubleshooting session. Confirmed via git history that AE-0284
restyled the siblings but skipped the progress sub-tree; two stale tokens proven (purple
`--color-primary`, undefined `--color-text`).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
