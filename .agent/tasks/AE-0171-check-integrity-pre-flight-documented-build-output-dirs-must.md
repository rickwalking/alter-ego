# AE-0171 — check-integrity pre-flight: documented build-output dirs must be gitignored

Status: Intake
Tier: T1
Priority: Medium
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Branch: TBD
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

- [ ] The pre-flight FAILS on a SEEDED build output that isn't gitignored (e.g. temporarily remove `/storybook-static/` from `.gitignore`) and passes on the real repo.
- [ ] Wired so it runs in CI / as part of integrity; clear remediation message.
- [ ] Current repo passes (all documented build outputs are ignored).

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
