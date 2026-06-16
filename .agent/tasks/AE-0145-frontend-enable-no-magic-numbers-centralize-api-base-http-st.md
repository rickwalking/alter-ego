# AE-0145 — Frontend: enable no-magic-numbers + centralize API_BASE/HTTP_STATUS literals

Status: Ready
Tier: T2
Priority: High
Type: Refactor
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Enforce the existing "no magic numbers/strings, constants centralized"
convention in the frontend lint gate, and centralize the shared literals the
reviewer flagged.

## Problem

Source: kaizen incident on PR #21 (`.agent/reports/kaizen-pr21.plan.md`). The
reviewer flagged magic values 3–4 times although `frontend/CLAUDE.md` already
forbids them and the constants exist:
- `knowledge/hooks/use-upload.ts:39` uses magic `200`/`300` while
  `frontend/src/constants/api.ts` already exports `HTTP_STATUS`.
- `API_BASE = "/api"` is duplicated in `blog/hooks/use-blog-posts.ts:16`,
  `quality/hooks/use-rubrics.ts:13`, `persona/hooks/use-personas.ts:13`
  ("Is it possible to have this variable globally available?").
`@typescript-eslint/no-magic-numbers` is available but not enabled.

## Scope

- Enable `@typescript-eslint/no-magic-numbers` in `frontend/eslint.config.mjs`
  (`ignore: [0, 1, -1]`, `ignoreEnums`, `ignoreReadonlyClassProperties`), error
  on changed files via `lint:changed`.
- Export `API_BASE` from `frontend/src/constants/api.ts`; replace the three
  duplicated literals with the import.
- Migrate `use-upload.ts` status checks to `HTTP_STATUS`.

## Non-Goals

- Repo-wide magic-number cleanup of untouched files (changed-files scope first).

## Acceptance Criteria

- [ ] `no-magic-numbers` enabled; `npm run lint:changed` fails on a seeded magic number.
- [ ] `API_BASE` exported from `constants/api.ts`; the three hooks import it; no bare `"/api"` remains in them.
- [ ] `use-upload.ts` uses `HTTP_STATUS` constants, no raw `200`/`300`.
- [ ] `bash scripts/ci/gates.sh frontend:lint-changed` passes on the cleaned tree.

## Gherkin Scenarios

```gherkin
Feature: Magic-number and shared-literal enforcement

  Scenario: New magic number on a changed line is rejected
    Given no-magic-numbers is enabled
    When a changed file introduces "if (status === 418)"
    Then the frontend lint-changed gate fails

  Scenario: Shared API base is centralized
    Given API_BASE is exported from constants/api.ts
    When a hook needs the API base
    Then it imports API_BASE instead of re-declaring "/api"
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
