# AE-0167 — Add CI build gate and group quality gates into frontend/backend categories (keep gates.sh)

Status: Intake
Tier: T2
Priority: High
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
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

- [ ] `gates.sh frontend:build` runs `npm run build` and FAILS on a seeded build-only break (e.g. a hook missing `"use client"`); passes on the real tree.
- [ ] The build gate runs as a blocking CI job on PRs.
- [ ] CI jobs grouped into frontend/backend categories (workflow files and/or `<area> / <gate>` naming) with no gate dropped; `gates.sh` unchanged as source of truth.
- [ ] Full gate suite green; `/qa-agent` still calls the same script.

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
