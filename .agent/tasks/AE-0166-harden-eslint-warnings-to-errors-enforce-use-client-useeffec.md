# AE-0166 — Harden ESLint: warnings to errors + enforce use-client, useEffect best-practice, and TanStack-Query-over-fetch rules

Status: Done
Tier: T2
Class: B
Priority: High
Type: Quality
Area: frontend
Owner: developer-skill
Agent Lane: planner → architect → developer → qa → release
Branch: chore/phase-8-class-b
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

- [x] ESLint severities audited (per-rule counts measured); promoted to `error`: `prefer-optional-chain` (fixed the 1), `no-console` (0), and `useEffect`+`fetch` (0). Kept at `warn` with a DOCUMENTED justification in `eslint.config.mjs` (promotion needs mass refactoring of pre-existing violations; diff-scoped `lint:changed` shrinks them): no-unnecessary-condition (69), prefer-nullish-coalescing (50), no-floating-promises (17), no-misused-promises (15), no-non-null-assertion (7), no-img-element (8), size/complexity rules. `npm run lint` (eslint --quiet) gates and PASSES.
- [x] Static `use-client` check (`scripts/check-use-client.mjs`, chained into `npm run lint`) flags a `.tsx` component using client-only hooks without `"use client"`; ERRORS on a seeded violation, PASSES on the real tree (171 files). Fixed 2 real violations (`create-carousel-{preview,progress}.tsx`). Tests: `src/scripts/use-client.test.ts`.
- [x] Data-fetching anti-pattern: `fetch` inside `useEffect` → **error** everywhere (0 violations), proven by a regression test (`src/scripts/eslint-fetch-rule.test.ts`) that lints a probe under `src/modules`. QA fix: a broader raw-`fetch` **warn** in a scoped `files: src/modules/components` block was REMOVED — ESLint flat config *replaces* (not merges) same-key `no-restricted-syntax` across config objects, so it had been silently downgrading the flagship `useEffect`-`fetch` error in exactly those directories. Broad raw-fetch steering, if wanted later, needs a non-colliding mechanism (a ratchet script), not `no-restricted-syntax`.
- [x] `react-hooks/exhaustive-deps` already `error`; repo clean (0 violations).
- [x] typecheck + `npm run lint` + 881 tests + `frontend:build` green; no new suppressions (check-integrity clean). Also fixed a typecheck error in the AE-0171 test (`NodeJS.ProcessEnv` → `Record<string,string>`) that vitest masked.

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

npm run lint PASS (eslint --quiet + use-client + boundaries/circular/component-types/dup); typecheck PASS; 881 vitest pass; frontend:build PASS. Seeded: console.log + fetch-in-useEffect -> ERROR; use-client missing -> ERROR; raw fetch in component -> WARN.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

ESLint hardened — warnings promoted to errors; use-client, useEffect best-practice, and TanStack-Query-over-fetch rules enforced in frontend/eslint.config.mjs (shipped #27). Verified in main.
