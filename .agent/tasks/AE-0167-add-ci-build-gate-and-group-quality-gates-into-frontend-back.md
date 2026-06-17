# AE-0167 — Add CI build gate and group quality gates into frontend/backend categories (keep gates.sh)

Status: Dev Complete
Tier: T2
Class: B
Priority: High
Type: Quality
Area: Cross-cutting
Owner: developer-skill
Agent Lane: planner → architect → developer → qa → release
Branch: chore/phase-8-class-b
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Add a CI **build gate** (no build runs in CI today) and reorganize the gate set into clear **frontend / backend quality-gate categories**, WITHOUT changing `scripts/ci/gates.sh` semantics (the single source of truth reused by `/qa-agent`). Source: kaizen sweep `.agent/reports/kaizen-sweep-2026-06-16.plan.md` P1 (broadened by owner).

## Problem

- Kaizen discovery: NO CI workflow runs `next build` and there is no `build` gate in `gates.sh` — so the missing-`"use client"` class (AE-0155) and any build-only breakage is caught NOWHERE in CI.
- The CI has grown many checks; the owner wants them grouped into categories ("frontend quality gates", "backend quality gates") for legibility, while keeping `gates.sh` intact (the QA phase depends on it).

## Scope

- Add a `frontend:build` gate to `gates.sh` running `npm run build`; wire it into CI as a blocking job.
- Group CI jobs into frontend vs backend categories. Feasible approaches (decide in design): keep per-area workflow files (`frontend-quality-gates.yml` + a `backend-quality-gates.yml`) and/or consistent `frontend / *` + `backend / *` job names; optionally a reusable workflow or grouped `needs`. Presentation/orchestration only.
- `gates.sh` stays canonical; CI keeps calling `bash scripts/ci/gates.sh <area>:<gate>`.

## Non-Goals

- No change to gate DEFINITION semantics in `gates.sh` (only ADD the build gate); QA-phase usage unchanged.
- Not removing or loosening any existing gate.

## Acceptance Criteria

- [x] `gates.sh frontend:build` runs `npm run build` and FAILS on a seeded build-only break (a server-component route using `useState` without `"use client"` → `next build` error "...mark the file with the 'use client' directive"); PASSES on the real tree.
- [x] The build gate runs as a blocking CI job on PRs (`frontend / Build` in `frontend-quality-gates.yml`).
- [x] CI jobs grouped into frontend/backend categories — ALREADY via the two per-area workflow files (`frontend-quality-gates.yml`, `backend-quality-gates.yml`) + `<area> / <gate>` job names; the new build job follows the same convention. No gate dropped; `gates.sh` only gained the `build` gate (definitions unchanged).
- [x] `gates.sh` stays canonical (`/qa-agent` calls the same script); `build` added to `--changed-only` skip (slow/whole-tree).

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

Seeded a server-component route using useState without "use client" -> `gates.sh frontend:build` FAIL ("...mark the file with the 'use client' directive"). Clean tree -> `frontend:build` PASS. tsc/lint unaffected.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
