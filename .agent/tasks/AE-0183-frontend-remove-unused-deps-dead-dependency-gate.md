# AE-0183 — Frontend: remove unused v1/shadcn deps + dead-dependency gate

Status: Ready
Tier: T2
Priority: Medium
Type: Task
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

> **Captured from** `.agent/reports/kaizen-frontend-debt.plan.md` (P1).
> **Relates to / may dedup against** AE-0152 (knip dead-export gate) + AE-0178
> (knip advisory) — overlapping; keep whichever the Phase-8 board prefers.

## Goal

Remove dead deps from the v1 (shadcn)→Tailwind migration; add a gate so dead deps can't re-accumulate.

## Problem

`npx depcheck` → 12 unused runtime deps: 8 `@radix-ui/*` (grep confirms 0 radix imports in src), `framer-motion`, `react-hook-form`, `client-only`, `server-only`.

## Scope

- Remove the 8 radix deps; verify-then-remove the others (+ `@hookform/resolvers` if react-hook-form goes).
- Add a knip/depcheck `frontend:deadcode-deps` gate with a config-only-devDep allowlist.

## Non-Goals

- Removing config-used devDeps depcheck false-flags (tailwindcss, typescript-eslint, @commitlint/*, stryker runner, prettier-plugin-tailwindcss).

## Acceptance Criteria

- [ ] Each dep removed ONE AT A TIME with `npm run build` + `typecheck` + `test` green after each (skeptical-review WARN).
- [ ] `framer-motion`/`react-hook-form` (declared stack) re-checked with wide `rg`; `client-only`/`server-only` checked for `import "x"` (no `from`).
- [ ] Gate FAILS on a seeded unused dep; config-only devDeps not false-flagged.

## Gherkin Scenarios

```gherkin
Feature: Dead-dependency gate
  Scenario: A newly-unused dependency is rejected
    Given the gate with a config-only allowlist
    When a dependency is imported nowhere
    Then scripts/ci/gates.sh frontend:deadcode-deps fails
```

## Decision Log

- 2026-06-17 — Skeptical review (WARN): added one-at-a-time build verification + wide rg + @hookform/resolvers coupling.

## Delta

### ADDED
- ...
### MODIFIED
- ...
### REMOVED
- ...

## Affected Areas

- Frontend:
- Tests:
- Docs:

## Dependencies

- Blocks:
- Blocked by:
- Related:

## Implementation Plan

1. See Scope.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-17 00:00

Captured from kaizen frontend-debt analysis (renumbered to free IDs; AE-0172..0182 owned by PR #29).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Final Summary

Pending.
