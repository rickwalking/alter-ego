# AE-0274 — Responsive create / carousel flow

Status: Planning
Tier: T2
Priority: High
Type: Feature
Area: frontend
Owner: Pedro Marins
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0274-responsive-create-flow
Kanban Card: TBD
Created: 2026-06-24
Updated: 2026-06-24
Parent: AE-0272
Depends-On: AE-0273

## Goal

Make the carousel create flow (brief form, workspace, publish) responsive: two-pane
layouts stack on mobile and go side-by-side at `md+`; progress steps scroll instead of
clipping; publish container reflows. Tailwind utilities only.

## Problem

`create/page.tsx:74` and `create/[id]/page.tsx:28` hardcode
`gridTemplateColumns:"1fr 360px"` (sidebar never stacks). `create-progress-steps.tsx:48`
has inline `overflow:"hidden"` (steps clip on mobile). `publish/page.tsx:172` uses
`maxWidth:"960px"` with `p-7` and a `space-between` header that crowds on phones.

## Scope

- `create/page.tsx`, `create/[id]/page.tsx`, `create/[id]/publish/page.tsx`,
  `create-progress-steps.tsx`, `create-sidebar.tsx` / `create-workspace-sidebar.tsx`.
- **Workspace section grids (GLM tree-sweep, were missed by the first audit):**
  `create/workspace/create-template-section.tsx:36` (`gridTemplateColumns:"repeat(3,1fr)"`)
  and `create/workspace/create-theme-section.tsx:57` (`"1fr 1fr"`) — both reflow to
  `grid-cols-1 sm:grid-cols-2`(theme) / `grid-cols-1 sm:grid-cols-2 md:grid-cols-3`(template).

## Non-Goals

- Shell/drawer (AE-0273). Functional changes to carousel generation.

## Design decisions (from GLM 5.2 review)

- **I1:** use `lg:grid-cols-[minmax(0,1fr)_360px]` → actually **`md:`** per I3
  (two-pane decoupled from shell): `grid-cols-1 gap-6 md:grid-cols-[minmax(0,1fr)_360px]`.
  `minmax(0,1fr)` (not bare `1fr`) to stop input/text blowout.
- **N4:** `create-progress-steps` inline `overflow:"hidden"` → `overflow-x-auto`; steps
  get `min-w` / `shrink-0` so they scroll on mobile, full row at `md+`.
- Publish: `maxWidth:"960px"` → `max-w-[960px] w-full`; padding `p-4 md:p-7`; header
  `flex-col gap-4 sm:flex-row sm:items-start sm:justify-between`.

## Acceptance Criteria

- [ ] Create form + workspace: single column on mobile, `md:grid-cols-[minmax(0,1fr)_360px]`
      side-by-side at `md+`; gap responsive; no overflow at 360px.
- [ ] Progress steps scroll horizontally on mobile (`overflow-x-auto`, no clip), full row
      at `md+`; each step ≥44px tall touch target. Publish "back to workspace" link and
      the form submit/CTA controls are ≥44px on coarse pointers.
- [ ] Workspace template/theme section grids reflow (no fixed `repeat(3,1fr)`/`1fr 1fr`
      inline) — `grid-cols-1` base, multi-col at `sm`/`md`.
- [ ] Publish: container `max-w-[960px] w-full`, `p-4 md:p-7`; header stacks on mobile,
      row at `sm+`; "back to workspace" link not crowded.
- [ ] Layout-critical inline styles on these files migrated to Tailwind classes (no
      remaining `gridTemplateColumns`/`overflow`/fixed `maxWidth` inline on layout).
- [ ] Neon identity unchanged; desktop visual diff ~nil.
- [ ] `gates.sh frontend` + lint + typecheck green; `.feature`/unit tests updated.

## Gherkin Scenarios

```gherkin
Feature: Responsive carousel create flow

  Scenario: Create form stacks on mobile
    Given the create page at 375px
    Then the form and the action sidebar are stacked in one column with no overflow

  Scenario: Two-pane at tablet width
    Given the create page at 768px
    Then the form and the 360px sidebar sit side by side

  Scenario: Progress steps scroll on mobile
    Given the create page at 375px
    Then the step indicator scrolls horizontally instead of clipping

  Scenario: Publish page reflows on mobile
    Given the publish page at 375px
    Then the container fits the viewport (no 960px overflow) and the header stacks vertically

  Scenario: Workspace template and theme grids reflow
    Given the create workspace at 375px
    Then the template and theme option grids render in a single column
```

## Delta

### MODIFIED
- `create/page.tsx`, `create/[id]/page.tsx`, `publish/page.tsx`,
  `create-progress-steps.tsx`, create sidebars — inline layout styles → Tailwind responsive.

## QA Checklist

- [ ] Lint + typecheck green; tests reference scenarios.
- [ ] 360 / 768 / 1024 — no overflow; sidebar stacks then splits at `md`.
</content>
