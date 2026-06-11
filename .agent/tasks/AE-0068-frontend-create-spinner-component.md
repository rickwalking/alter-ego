# AE-0068 — Frontend: create reusable Spinner component with React Suspense

Status: Intake
Tier: T2
Priority: Medium
Type: Feature
Area: Frontend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-11
Updated: 2026-06-11

## Goal

Fix PR #11 comment #24: "Create a spinner/loading component to reuse. Use React Suspense." in `frontend/src/features/publish/components/regenerate-strategy-section.tsx` (line 78).

## Problem

Loading states are handled inline without a shared spinner component. This leads to duplicated markup and inconsistent loading UX.

## Scope

- Create a reusable `<Spinner>` component in `src/components/ui/spinner.tsx` (already created by AE-0047 — verify it's correctly built)
- Wire the Spinner into React.Suspense boundaries where applicable
- Ensure the Spinner supports: size variants (sm, md, lg), optional label, and accessible aria attributes
- Replace inline loading spinners with the new component

## Non-Goals

- Do not change the existing layout or behavior outside of spinner replacement

## Acceptance Criteria

- [ ] `<Spinner>` component exists in `src/components/ui/`
- [ ] Supports size variants (sm, md, lg)
- [ ] Supports optional visible label
- [ ] Has proper aria attributes for accessibility
- [ ] All inline spinner/loading markup in `regenerate-strategy-section.tsx` uses the new component
- [ ] TypeScript compiles cleanly
- [ ] All tests pass

## Gherkin Scenarios

```gherkin
Feature: Spinner component

  Scenario: Default spinner renders
    Given a Spinner component
    When rendered without props
    Then it shows an animated loading indicator
    And has aria-busy="true"

  Scenario: Spinner with custom label
    Given a Spinner component
    When rendered with label="Loading..."
    Then it shows the label text alongside the spinner animation

  Scenario: Spinner in Suspense fallback
    Given a lazy-loaded component
    When wrapped in Suspense with Spinner as fallback
    Then the Spinner is shown while the component loads
```

## Affected Areas

- Frontend: `components/ui/spinner.tsx`, `features/publish/components/regenerate-strategy-section.tsx`

## Dependencies

- Blocks: None
- Blocked by: None
- Related: AE-0047 (spinner.tsx skeleton created)

## QA Checklist

- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked
