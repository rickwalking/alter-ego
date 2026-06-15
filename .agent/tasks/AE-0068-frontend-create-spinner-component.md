# AE-0068 — Frontend: create reusable Spinner component with React Suspense

Status: Review
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

## Modularization Alignment (2026-06-12)

Scope correction from the 2026-06-12 scan: **two spinner components
already exist** — `src/components/ui/spinner.tsx` and
`src/components/atoms/neon-spinner.tsx` (with stories). This ticket is
now a **consolidation**, not a creation:

- Pick the survivor: `components/atoms/neon-spinner.tsx` (plan rule:
  generic, domain-neutral components live in atoms; a parallel `ui/`
  taxonomy fragments atomic design).
- Fold `ui/spinner.tsx` capabilities (size/label/aria) into the atom,
  migrate its usages, delete the duplicate.
- Wire Suspense boundaries in `regenerate-strategy-section.tsx` per the
  original PR comment.
- AE-0047's spinner section is deleted and defers here (single owner).

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

- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Files Touched

- atoms/neon-spinner.tsx (+ labeled Spinner wrapper), atoms/index.ts
- features/publish/.../regenerate-strategy-section.tsx (import + Suspense)
- atoms/neon-spinner.test.tsx (new, 15); DELETED ui/spinner.tsx + test

## Test Evidence

```
typecheck: clean; lint: 0 errors
full frontend suite: 807 passed (71 files)
neon-spinner consolidated tests: 15 passed
```

## QA Report

✅ PASS — Wave 5 batch QA, 2 independent passes both PASS (F-1/F-3 fixed). See `.agent/reports/AE-0068.qa.md` → `.agent/reports/wave-5.qa.md`.Progress Log

### 2026-06-12

Consolidated spinners to atoms per 2026-06-12 alignment; Suspense boundary wired.
