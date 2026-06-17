# AE-0171 — check-integrity pre-flight: documented build-output dirs must be gitignored

Status: Dev Complete
Tier: T1
Class: B
Priority: Medium
Type: Quality
Area: Cross-cutting
Owner: developer-skill
Branch: chore/phase-8-class-b
Created: 2026-06-16
Updated: 2026-06-16

## Goal

A pre-flight check that fails if any documented build command's output directory is not gitignored — so build artifacts never pollute lint/QA again. Source: kaizen sweep `.agent/reports/kaizen-sweep-2026-06-16.plan.md` P6.

## Problem

`npm run build-storybook` writes `storybook-static/`, which was NOT gitignored; when present it broke `eslint` (parse errors on built JS) during AE-0154 end-of-phase QA until gitignored by hand. There is no guard ensuring every documented build target's output is ignored, so the next new build command can repeat this.

## Scope

- Add a check (in `scripts/ci/check-integrity.sh` or a small dedicated `scripts/ci` script it calls) that, for each known build command (`next build`→`.next`, `build-storybook`→`storybook-static`, coverage, playwright-report, etc.), asserts the output dir is matched by `.gitignore`.
- Source the list from a small explicit map (kept next to the check) so adding a build command forces adding its ignore.
- Fail with a clear message naming the missing ignore entry.

## Non-Goals

- Not auto-editing `.gitignore` (the check just enforces; the dev adds the entry).
- Not loosening any gate.

## Acceptance Criteria

- [x] The pre-flight FAILS on a SEEDED non-ignored build output and passes on the real repo. Verified by `frontend/src/scripts/build-output-ignored.test.ts` (3 tests) + manual seed.
- [x] Wired so it runs as part of integrity (`scripts/ci/check-integrity.sh` calls it before the scan) with a clear remediation message naming the missing path.
- [x] Current repo passes (9 outputs checked). **Fixed a real gap:** `backend/coverage.xml` and `backend/.coverage` were COMMITTED artifacts — untracked (`git rm --cached`) + added to `backend/.gitignore`.

## Test Evidence

`bash scripts/ci/check-build-output-ignored.sh` → "pre-flight OK (9 outputs checked)".
Seeded map with a non-ignored path → exit 1 naming it.
`npx vitest run src/scripts/build-output-ignored.test.ts` → 3 passed.
`check-integrity.sh frontend` runs the pre-flight (OK) then the scan (0 blockers).

## Repro Steps

1. Run `npm run build-storybook` (creates `storybook-static/`), then `npm run lint` → eslint parse errors on the built JS (the AE-0154 incident) when the dir isn't ignored.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

None.

## Progress Log

### 2026-06-16 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
