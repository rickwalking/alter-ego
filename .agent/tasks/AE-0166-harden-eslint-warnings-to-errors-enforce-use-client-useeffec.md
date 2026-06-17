# AE-0166 — Harden ESLint: warnings to errors + enforce use-client, useEffect best-practice, and TanStack-Query-over-fetch rules

Status: Intake
Tier: T2
Priority: High
Type: Quality
Area: frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Raise the frontend ESLint bar so whole classes of bugs are caught statically (as ERRORS, not warnings) instead of at build/review/runtime. Source: kaizen sweep `.agent/reports/kaizen-sweep-2026-06-16.plan.md` P2 (broadened by owner).

## Problem

Failure classes from the kaizen sweep:
- A missing `"use client"` directive was caught ONLY by `npm run build` (AE-0155), not by lint/typecheck/test — there is no static rule for React-hook usage in RSC-reachable module files.
- Owner directive: ESLint currently `warns` for many rules; warnings are ignored. Most should be `error`. Also enforce code-quality rules in-repo: best-practice `useEffect` usage (avoid complex/buggy effects) and BAN raw `fetch`/`useEffect`-data-fetching in favor of TanStack Query (per `frontend/CLAUDE.md` "NEVER use useEffect for Data Fetching").

## Scope

- Promote ESLint rule severities from `warn` to `error` wherever feasible (audit `eslint.config.mjs`; keep only justified exceptions).
- Add a rule enforcing `"use client"` when a module/component/hook file uses client-only React APIs (`useState`/`useEffect`/`useRef`/etc.) — research the canonical plugin rule (e.g. `react-server-components`/next rules) or a custom `scripts/` lint check mirroring the boundary checkers.
- Add/enable rules discouraging data-fetching in `useEffect` and raw `fetch` in components/hooks (steer to TanStack Query + `authenticated-fetch`), and `react-hooks/exhaustive-deps` as error.
- Keep the down-only ratchet philosophy: any newly-flagged existing violations are fixed or baselined-to-shrink, never blanket-ignored.

## Non-Goals

- Not loosening any rule (ratchet UP only). No blanket `eslint-disable`.
- Not a backend lint change (that is ruff, already strict).

## Acceptance Criteria

- [ ] ESLint rule severities audited; warnings promoted to `error` except documented, justified exceptions; `npm run lint` (eslint --quiet) still gates and passes.
- [ ] A static rule flags client-only React API usage without `"use client"` in `src/modules/**`/`src/components/**`; it ERRORS on a SEEDED violation (a hook using `useState` without the directive) and passes on the real tree.
- [ ] A rule bans data-fetching `useEffect` + raw `fetch` in components/hooks (steering to TanStack Query); ERRORS on a seeded violation.
- [ ] `react-hooks/exhaustive-deps` (and related) set to `error`; repo is clean or violations are fixed (not ignored).
- [ ] typecheck + full `npm run lint` + 823 tests + build green; no new suppressions introduced (check-integrity clean).

## Gherkin Scenarios

```gherkin
Feature: ...

  Scenario: ...
    Given ...
    When ...
    Then ...
```

## Delta

### ADDED

- ...

### MODIFIED

- ...

### REMOVED

- ...

## Affected Areas

- Backend:
- Frontend:
- Database:
- API:
- Tests:
- Docs:
- Prompts/LLM:
- Observability:
- Deployment:

## Dependencies

- Blocks:
- Blocked by:
- Related:

## Implementation Plan

1. ...

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16 HH:mm

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
