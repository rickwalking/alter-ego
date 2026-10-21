# AE-0446 — Gardener: 5-level QA scan, strict lint/tsc, dead code + duplication cleanup

Status: In Development
Tier: T2
Priority: Medium
Type: Chore
Area: Cross-cutting
Owner: Claude (gardener worker)
Agent Lane: developer → qa → release
Branch: chore/ae-0446-<level> (one PR per level/theme, base main)
Kanban Card: TBD
Created: 2026-10-21
Updated: 2026-10-21

## Goal

Scan the whole codebase on fresh `origin/main` at five QA levels, fix what is
found, and ratchet the static gates up (warn → error, stricter tsc, warnings as
errors in pytest) without weakening anything. Shipped as small PRs per level.

## Problem

Owner request (2026-10-20). The ESLint config still carried advisory `warn`
rules (AE-0166 backlog), tsc lacked several strict flags, pytest printed
~4.6k warnings, and the AE-0441 knip pass plus the 2026-10-20/21 reviews left
follow-ups (soft 404 on `/carousels/<unknown>`, the carousel 404 detail leaking
existence, a mixed-language landing card, unlisted/unused deps).

## Scope

- Level 1 — static correctness: tsc strict flags, ESLint warn → error,
  `--max-warnings=0` on every lint path, pytest `filterwarnings = error`.
- Level 2 — dead code + duplication: knip, vulture, jscpd.
- Level 3 — tests (no mutation): flaky/skipped/xfail without reason, coverage
  gaps, Gherkin scenarios without a test reference.
- Level 4 — security + dependencies: bandit, pip-audit, npm audit, gitleaks.
- Level 5 — integrity, contracts, PR hygiene: integrity gate, schema/OpenAPI
  drift, ticket validator, still-valid "missing X" findings on PRs since #143.
- The known follow-ups listed in the gardener brief.

## Non-Goals

- Mutation testing (never run locally; CI is the source of truth).
- Behavior changes beyond the listed follow-ups.

## Acceptance Criteria

- [x] L1: `noImplicitOverride` + `noUncheckedIndexedAccess` enabled, tsc clean.
- [x] L1: `no-unnecessary-condition` + `prefer-nullish-coalescing` promoted to
      `error` with a rule-fires test.
- [ ] L1: size/complexity rules promoted to `error`; every lint script/CI path
      uses `--max-warnings=0`.
- [ ] L1: backend pytest runs with `filterwarnings = error`; own warnings fixed,
      third-party ignores justified.
- [ ] L2: real dead code removed, knip false positives configured with a reason,
      real duplication extracted.
- [ ] L3/L4/L5: findings fixed or documented as accepted below.
- [ ] Known follow-ups fixed (carousel 404 parity, soft 404, landing card language,
      knip deps, `DEAD_CODE_FULL_TREE_BLOCKING=1`).
- [ ] Every PR reproduces `gates.sh` (backend + frontend, all but mutation) green.

## Gherkin Scenarios

Level-1/2 PRs are pure refactors and CI/config work (no public or user-visible
behavior change), so per AE-0153 they ship focused unit tests plus the gate's
seeded-violation test instead of a `.feature`. The follow-up PR that changes
HTTP behavior (404 parity, soft 404) ships its own `.feature` scenarios.

```gherkin
Feature: Strict type-aware lint rules gate the build

  Scenario: An unnecessary nullish fallback fails the lint
    Given a production module that applies ?? to a non-nullable value
    When ESLint runs
    Then @typescript-eslint/no-unnecessary-condition reports an error

  Scenario: A logical-or over a nullable value fails the lint
    Given a production module that uses || on a string | null
    When ESLint runs
    Then @typescript-eslint/prefer-nullish-coalescing reports an error
```

## Delta

### ADDED

- `frontend/src/lib/utils.ts` `firstNonBlank()` (display fallback that skips blank strings).
- `frontend/src/scripts/eslint-strict-type-rules.test.ts` (rule-fires test).

### MODIFIED

- `frontend/tsconfig.json`, `frontend/eslint.config.mjs`, ~80 frontend files (see PRs).

### REMOVED

- Dead `?? []` / `?? DEFAULT` fallbacks for fields the backend schema always sends.

## Affected Areas

- Backend: pytest config, deprecation fixes (L1 backend PR); dead code (L2).
- Frontend: tsconfig, ESLint config, type-narrowing fixes.
- Database: none.
- API: none in L1/L2; 404 parity in the follow-up PR.
- Tests: test fixtures adapted to `noUncheckedIndexedAccess`; new rule-fires test.
- Docs: this ticket.
- Prompts/LLM: none.
- Observability: none.
- Deployment: none.

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0166, AE-0180, AE-0441

## Implementation Plan

1. L1 frontend strict types (PR 1).
2. L1 frontend size/complexity warn → error + `--max-warnings=0` (PR 2).
3. L1 backend warnings as errors (PR 3).
4. L2 dead code + duplication (PR 4).
5. Follow-ups + L3–L5 fixes (PR 5+).

## Findings — Level 1 (static correctness)

| Tool / check | Before | After | Fixed | Deferred + reason |
| --- | --- | --- | --- | --- |
| tsc (repo config) | 0 | 0 | — | — |
| tsc `noImplicitOverride` | 0 | 0 | enabled | — |
| tsc `noUncheckedIndexedAccess` | 237 (34 prod, 203 tests) | 0 | enabled; prod: real guards (destructure + `undefined` check, non-empty tuple type for `POV_TEMPLATES`); tests: `!` on fixtures (allowed by the test override) | — |
| tsc `exactOptionalPropertyTypes` | 58 (45 prod) | 58 | — | Deferred: nearly all are "optional prop receives `T \| undefined` from its parent"; the fix is widening ~40 prop interfaces to `?: T \| undefined`, which adds noise without catching a real bug here, plus third-party config types (`next.config.ts`, `playwright.config.ts`). |
| ESLint `no-unnecessary-condition` | 65 warn | 0, now `error` | promoted | — |
| ESLint `prefer-nullish-coalescing` | 5 warn | 0, now `error` | promoted | — |
| ESLint size/complexity (`max-lines-per-function` 43, `complexity` 39, `max-lines` 17, `max-statements` 7, `sonarjs/cognitive-complexity` 5) | 111 warn | pending | PR 2 | — |
| pytest warnings | 4604 | pending | PR 3 | — |

Root causes found while paying down `no-unnecessary-condition` (real defects, not lint noise):

- `isFullWorkflowState` was a type predicate claiming the full
  `EditorialWorkflowState` while accepting payloads without `project_id` or
  `current_phase`; narrowed to the fields it verifies.
- SSE token/error handlers did `(data.content as string) ?? ""`: the cast made a
  missing `content` untypeable; replaced with `typeof` guards.
- Knowledge document tags cast free-form metadata to `string[]`; now filtered.

## Findings — Level 2 (dead code + duplication)

Scan (2026-10-21, Haiku scanner): knip 0 unused files/exports/types, 7 unused
devDependencies (mostly tool/config uses), 2 unlisted (`postcss`, `micromatch`),
1 duplicate export (`FLAT_EDITORIAL_PRESET`/`DEFAULT_IMAGE_PRESET`); dead-code gate
0 (also with `DEAD_CODE_FULL_TREE_BLOCKING=1`); vulture@80 0, vulture@60 608
(mostly FastAPI/pydantic false positives, ~15 real candidates); jscpd frontend 22
clones, backend 26 clones. Fixes: pending (PR 4).

## Findings — Level 4 (security + dependencies)

| Tool | Result | Action |
| --- | --- | --- |
| bandit | 12 (1 high B701, 1 medium B104, 10 low B105/B107) | All false positive / accepted: B701 renders LLM prompt markdown (not HTML); B104 bind 0.0.0.0 is required in the container; B105/B107 are cookie/header/field-name constants. |
| pip-audit | pass (2 ignored IDs) | Ignores `PYSEC-2022-42969`, `PYSEC-2026-196` are undocumented: document reason (pending). |
| npm audit (prod) | 0 | — |
| npm audit (all) | 11 moderate, dev-only (`@vitest/mocker` via storybook) | Accepted: dev-only, fix is a breaking `--force` upgrade. |
| gitleaks | 2 | Both false positives (prose in a report, a numeric test fixture). |

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-21 07:10

Took over from the DeepSeek worker (free-usage limit). Reviewed its uncommitted
Level-1 diff: kept the `??` / typed `response.json()` fixes and `firstNonBlank`
(made it return the trimmed value, as the `?.trim() ||` callers did); replaced
its `.at(index)` change (negative indexes wrap) with `noUncheckedIndexedAccess`.

## Files Touched

See each PR.

## Test Evidence

PR 1: `npx tsc --noEmit` 0 errors; `npm run lint` exit 0; vitest 216 files /
1757 tests passed; rule-fires test fails when a rule is set back to `warn`.

## QA Report

Pending.

## Decision Log

- `exactOptionalPropertyTypes` deferred (see Level 1 table).
- Test fixtures use `!` for `noUncheckedIndexedAccess` (the test override already
  allows `no-non-null-assertion`; fixtures are known-present).
- Types that match the backend response schema (e.g. `research_findings`,
  `lock_version` with `default_factory` / defaults) are trusted; the dead fallbacks
  were removed rather than the types loosened.

## Blockers

None.

## Final Summary

Pending.
