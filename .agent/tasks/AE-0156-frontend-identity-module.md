# AE-0156 — Frontend: modules/identity — consolidate auth/session behind a public contract

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0156-frontend-identity-module
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Consolidate frontend auth/session (currently in lib/jwt-auth, lib/auth-cookie, lib/authenticated-fetch, app/api/auth/*, app/login, app/(admin)) into a modules/identity bounded context behind a public contract, completing the 9-context glossary.

## Problem

Phase 7 deferred identity because auth/session is route-adjacent (guards + sign-in pages) and risky to relocate behavior-preservingly. It remains the one glossary context without a module.

## Scope

Create modules/identity with a public barrel; move the auth/session client logic from lib/ (and the colocatable parts of app/) behind it; route consumers through @/modules/identity; keep route-level guards + App Router auth behavior byte-identical (re-export shims where a lib/ path must keep resolving). Highest-risk Class-A slice — lean on e2e/route smoke.

## Non-Goals

- No auth BEHAVIOR change (same tokens/cookies/guards/redirects).
- No App Router URL change; route handlers under app/api/auth keep their paths.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] modules/identity SHALL own auth/session behind a public contract; consumers import @/modules/identity
- [ ] Auth behavior byte-identical (login/logout/guards/refresh); App Router URLs unchanged
- [ ] typecheck + lint (boundary 0/0) + 822 tests + build + check:legacy green

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (and, for the Class-B behavior
change, by the updated AE-0125 safety net asserting the new approval≠release flow).

## Dependencies

- Blocks: AE-0157, AE-0161
- Blocked by: AE-0153
- Related: AE-0152

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by planner (Phase 8 breakdown).

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
