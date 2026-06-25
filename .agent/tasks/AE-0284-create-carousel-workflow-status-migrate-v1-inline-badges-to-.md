# AE-0284 — create-carousel workflow status: migrate v1 inline badges to v2 neon semantic status badge

Status: Intake
Tier: T2
Priority: P2
Type: Bugfix
Area: frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-25
Updated: 2026-06-25

## Goal

Replace the create-carousel workflow's v1 status indicators with a single,
**semantic** v2 status badge (`WorkflowStatusBadge` over the existing `NeonBadge`
atom). The status colour reflects the actual workflow state everywhere it
appears, with a consistent component vocabulary across the create flow.

## Problem

(User-reported; visually reproduced via Playwright at 1440 —
`create-workspace-status-1440.png`. Redesign planned via `/impeccable shape`,
product register; user approved full scope + the semantic colour map.)

The create-carousel "status" is still v1:
- `create/workspace/project-summary-card.tsx:67-80` — the "Status" pill is an
  **inline-styled** `<span>` that is **always amber regardless of state** (Draft,
  "Ready to publish", and Failed all render the same warning-amber). Colour
  carries no meaning and it doesn't use the `NeonBadge` atom.
- `create/workspace/create-workspace-sidebar.tsx:96-119` — the "Active phase"
  status is a raw `<span>` with an inline conditional colour (NEON_RED on failed,
  else NEON_CYAN); no component, two states only.
- `create-workflow-panel.tsx:238` / `create-workflow-artifacts.tsx:60` already
  use `NeonBadge` but hardcode `variant="secondary"`, so the same status renders
  differently in different places (inconsistent vocabulary).
- `create-progress-steps.tsx:54-106` applies Neon colour constants via inline
  `style={}` objects and a hardcoded `rgba(255,255,255,0.04)` pending fill instead
  of Neon token classes.

`NeonBadge` (`@/components/atoms/neon-badge.tsx`, variants
cyan/magenta/teal/amber/green/red + size + optional dot) is the canonical v2
status atom. See `phase-item.tsx` / `phase-progress-detail.tsx` for the v2 token
vocabulary to match.

## Scope

- **New `WorkflowStatusBadge`** (atom-level wrapper over `NeonBadge`) + a pure
  `resolveWorkflowStatus(status, phase?)` map → `{ variant, dot, labelKey }`.
  Semantic mapping (approved by the user):
  | status | variant | dot |
  |--------|---------|-----|
  | `pending` / draft | `amber` | — |
  | `in_progress` | `cyan` | pulse |
  | `awaiting_human` | `magenta` | yes |
  | `approved` / `approved_for_publish` | `teal` | — |
  | published / completed | `green` | — |
  | `rejected` / `failed` | `red` | — |
  | unknown | `cyan` (default) | — |
  Labels via i18n (no hardcoded English, no `text-transform` on the raw enum).
- **Migrate** `project-summary-card.tsx` + `create-workspace-sidebar.tsx` to the
  badge; **route** the two existing `NeonBadge variant="secondary"` usages
  (`create-workflow-panel`, `create-workflow-artifacts`) through the same map.
- **Stepper cleanup** (`create-progress-steps.tsx`): inline `style={}` colour
  objects + hardcoded `rgba(255,255,255,0.04)` → Neon token classes/constants;
  same rendered result.
- Unit tests (the map, incl. unknown fallback), a render test, a Storybook story,
  and a `.feature` file.

## Non-Goals

- No backend/API change; consumes the existing `phase_status` / workflow status.
- No layout/IA change to the workspace, sidebar, or summary card beyond the badge.
- Not redesigning the already-v2 components (`phase-item`,
  `phase-progress-detail`, `create-carousel-progress`).

## Acceptance Criteria

- [ ] A single `WorkflowStatusBadge` renders the status everywhere it appears in
      the create flow (summary card, sidebar, workflow panel/artifacts); the same
      status looks identical in every location.
- [ ] Badge colour is **semantic** (per the map); a "Ready to publish" or
      "Failed" status no longer shows warning-amber.
- [ ] Status is conveyed by **text label + colour + dot** (never colour alone);
      `in_progress` shows a pulsing dot that is static under
      `prefers-reduced-motion`.
- [ ] No inline-styled status `<span>` remains in `project-summary-card` /
      `create-workspace-sidebar`; `create-progress-steps` uses Neon token classes,
      not inline colour objects or `rgba(255,255,255,0.04)`.
- [ ] `resolveWorkflowStatus()` is unit-tested for every status + the unknown
      fallback; `.feature` added; Storybook story shows all states.
- [ ] `bash scripts/ci/gates.sh frontend` green (17/17); verified via Playwright
      MCP at 390 + 1440; Neon identity unchanged.

## Gherkin Scenarios

```gherkin
Feature: Create-carousel workflow status badge

  Scenario: status colour reflects state
    Given a carousel project whose workflow status is "failed"
    When the workspace renders the Project Summary
    Then the Status badge is the red (error) variant, not amber

  Scenario: live state shows a pulsing dot
    Given a project whose status is "in_progress"
    When the status badge renders
    Then it is the cyan variant with a leading dot
    And the dot does not animate under prefers-reduced-motion

  Scenario: consistent vocabulary across the flow
    Given the same status appears in the summary card and the workflow panel
    Then both render the identical WorkflowStatusBadge variant and label

  Scenario: unknown status falls back safely
    Given a status value not in the map
    When resolveWorkflowStatus runs
    Then it returns the default cyan variant with the titlecased label
```

## Delta

### ADDED

- `…/create/workspace/workflow-status-badge.tsx` + `workflow-status.ts` (map)
- unit tests, render test, Storybook story, `.feature`

### MODIFIED

- `project-summary-card.tsx`, `create-workspace-sidebar.tsx`,
  `create-workflow-panel.tsx`, `create-workflow-artifacts.tsx`,
  `create-progress-steps.tsx`; i18n message catalog (status labels)

### REMOVED

- inline-styled status `<span>`s; hardcoded `rgba(255,255,255,0.04)` pending fill;
  the always-amber status pill

## Affected Areas

- Backend: none
- Frontend: create-carousel workspace status surfaces + a new atom
- Database: none
- API: none (consumes existing status)
- Tests: map unit tests + render test + `.feature`; Storybook story
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks:
- Blocked by:
- Related: `/impeccable shape` plan (this session), AE-0272 (responsive shell),
  NeonBadge atom

## Implementation Plan

1. `workflow-status.ts`: `resolveWorkflowStatus()` map + i18n label keys.
2. `workflow-status-badge.tsx`: NeonBadge wrapper (variant/dot/label, a11y
   `role="status"`, reduced-motion dot).
3. Migrate the 2 inline call sites + route the 2 existing NeonBadges.
4. Stepper token cleanup.
5. Unit tests + render test + Storybook + `.feature`; `gates.sh frontend`;
   Playwright verify at 390 + 1440.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-25 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
