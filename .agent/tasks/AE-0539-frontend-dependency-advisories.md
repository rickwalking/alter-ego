# AE-0539 — Frontend: clear the new npm audit advisories (zod, vitest, storybook)

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Frontend
Owner: Claude — found while shipping the chat polish (AE-0535)
Branch: fix/ae-0539-frontend-advisories
Created: 2026-10-23
Updated: 2026-10-23

## Goal

`frontend:security` (`npm audit --audit-level=high`) passes again, so frontend pull requests (main included) can go
green, and the moderate advisories are cleared too.

## Problem

New advisories made `npm audit` report 12 vulnerabilities on main:
- HIGH zod <4.6.6 (GHSA-mrhx-c7xc-m3w5): the app's own zod 3.25 and the zod nested under Stryker's
  `mutation-server-protocol` (no 3.x release is patched).
- MODERATE vitest / @vitest/mocker <4.1.12 (GHSA-82fw-gwwq-j7x9, GHSA-qxg6-89mg-rqv8), and storybook 9.x, which pins
  @vitest/mocker 3.2.4 (no patched 3.x; storybook is patched from 10.1.0).

## Scope

- vitest and @vitest/coverage-v8 ^4.1.12 (patch release).
- storybook, @storybook/react, @storybook/nextjs-vite, @storybook/addon-a11y ^10.6.3 (major: Storybook 10 is ESM
  only, so `.storybook/main.ts` resolves its directory from `import.meta.url` instead of `__dirname`).
- zod ^4.6.7 for the app (major) plus an `overrides` entry pinning zod ^4.6.7 under `mutation-server-protocol`.
  Minimal zod 4 changes: object fields typed `z.unknown()` are `.optional()` (zod 3 treated them as optional; zod 4
  requires the key, which broke the `{success:false, error}` envelope parse), `z.record` takes key and value
  schemas, and deprecated APIs are replaced (`ZodSchema` -> `ZodType`, `ZodIssue` -> `z.core.$ZodIssue`,
  `.passthrough()` -> `.loose()`, `z.string().uuid()` -> `z.uuid()`).

## Non-Goals

- Any other dependency change; no audit ignore list, no lowered audit level, no skips.

## Acceptance Criteria

- [x] `frontend:security` passes (`npm audit`: 0 vulnerabilities).
- [x] lint, typecheck, the full vitest suite and schema-drift pass; Storybook builds.
- [x] Stryker still loads (version, config and vitest runner); mutation runs in CI only.

## Repro Steps

1. `bash scripts/ci/gates.sh frontend:security` on main -> 1 high (12 total). On this branch -> PASS, 0 found.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-23 23:30

Bumped and locked. No public or user-visible behaviour change is intended: this is a dependency/CI ticket, so per
CLAUDE.md (AE-0153) the gates and unit tests stand in for a `.feature`; the failing `frontend:security` gate on main
is the seeded check, and the full vitest suite (2790 tests, incl. the API-client envelope tests that caught the zod
4 optional-key change) guards the schema behaviour. Affected gates: frontend:security, lint, typecheck, test,
schema-drift, build. The no-`.feature` classification is for QA to confirm.

## Files Touched

- frontend/package.json, frontend/package-lock.json, frontend/.storybook/main.ts
- frontend/src/lib/api-client.ts, src/lib/server-fetch.ts, src/lib/zod-field-errors.ts
- frontend/src/schemas/chat.ts, knowledge.ts, carousel.ts; src/modules/publishing/distribution/hooks/use-edit-carousel-slides.ts

## Test Evidence

npm audit: 0 vulnerabilities. frontend gates (--changed-only): 15 PASS, 0 FAIL; schema-drift PASS; full vitest
2790 passed; `storybook build` succeeds; `stryker --version` 9.6.1, vitest runner and mutation-server-protocol load.

## QA Report

See `.agent/reports/AE-0539.qa.md`.

## Blockers

None.
