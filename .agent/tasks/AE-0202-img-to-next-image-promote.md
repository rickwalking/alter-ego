# AE-0202 — Frontend: migrate img->next/image, fix dead exemption glob, promote no-img-element

Status: Dev Complete
Tier: T2
Priority: Medium
Type: Refactor
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal
Remove raw <img>, fix a stale eslint exemption, and lock the rule.

## Problem
Source: kaizen production-readiness sweep. 7 prod `<img>` flagged. The eslint exemption glob
`src/features/blog/components/public-post/**` is DEAD (files moved to
`src/modules/publishing/blog/components/public-post/**`), so it exempts nothing.

## Scope
- Fix/remove the stale exemption glob in eslint.config.mjs.
- Migrate the 7 `<img>` to `next/image` (set dimensions / remotePatterns; test layout).
- Flip `@next/next/no-img-element` warn→error.

## Non-Goals
- Unrelated image refactors.

## Acceptance Criteria
- [x] 0 no-img-element findings in production `src`; rule promoted warn→error;
      layout preserved (fill + aspect-ratio + object-contain); build + 888 tests green.
- [x] **Seeded `<img>` ERRORS** (severity 2) — `src/scripts/eslint-no-img-rule.test.ts`.

## Gherkin Scenarios
```gherkin
Feature: next/image enforced
  Scenario: raw img blocked
    Given the rule promoted to error and the glob fixed
    When a component uses <img>
    Then lint fails
```

## Delta
### ADDED
- ...
### MODIFIED
- ...
### REMOVED
- ...

## Affected Areas
- Frontend:
- Docs:
- Tests:

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
Emitted by kaizen production-readiness sweep (.agent/reports/kaizen-production-readiness.plan.md).

### 2026-06-17 (executed, dev→QA loop, PR #31)
PARTIAL — 6/7 img→next/image + dead glob removed; rule stays warn (1 case) [commit 47d8a00]. QA: integrity 0 blockers, eslint 0 errors, 884 FE tests pass.

## Files Touched
- `frontend/src/modules/publishing/blog/components/image-gen-modal.tsx` — last prod
  `<img>` → next/image (`fill` + `relative aspect-square` container + `object-contain`
  + `unoptimized`; dimension-agnostic for the backend-generated preview).
- `frontend/eslint.config.mjs` — `no-img-element` warn→error; removed the dead
  justification comment; test-file block exempts the rule (next/image mock pattern).
- `frontend/eslint-rule-override-allowlist.json` — allow-list entry for the
  test-block re-declare (forced by the AE-0179 guard — a nice dogfood).
- `frontend/src/scripts/eslint-no-img-rule.test.ts` (new) — seeded `<img>` → error.

## Test Evidence

PATH TAKEN: genuine fix (modal migrated, rule flipped to error). The modal preview
renders correctly with `fill`/`object-contain`; build + full test suite green.

```bash
$ bash scripts/ci/gates.sh frontend:build  -> PASS
$ bash scripts/ci/gates.sh frontend:test   -> PASS (90 files, 888 tests)
$ bash scripts/ci/gates.sh frontend:lint   -> PASS (no-img-element now error)
$ npx vitest run src/scripts/eslint-no-img-rule.test.ts -> 1 passed (seeded <img> = severity 2)
$ bash scripts/ci/check-integrity.sh frontend -> 0 blockers
```
The one remaining `<img>` is the **next/image mock** in
`horizontal-carousel-viewer.test.tsx` (a test mocking next/image with a plain
`<img>`); exempted via the test-file block, NOT a production finding.

## QA Report
Pending.
## Decision Log
- Modal preview uses `unoptimized` because the URL is a freshly generated backend
  asset; `fill` + fixed aspect ratio handles the unknown intrinsic dimensions
  (the original ticket's blocker) without a behavior change.
- Test-file `no-img-element: off` is the documented test-exemption pattern (matches
  no-non-null-assertion / no-magic-numbers), not a gaming suppression — production
  stays `error`. The AE-0179 guard required (and got) a justified allow-list entry.
## Blockers
None.
## Final Summary
Pending.
