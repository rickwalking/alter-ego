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

SLICE 1 of identity (route handlers/guards are the separate AE-0164 slice): move the auth/session-SPECIFIC client lib (lib/jwt-auth, lib/auth-cookie, the auth client surface) into a modules/identity bounded context behind a public contract. CRITICAL SCOPE BOUND: lib/authenticated-fetch + lib/server-fetch are the APP-WIDE HTTP client (used by every module — not auth-specific) and STAY in lib/ as platform infra; they are NOT moved into identity.

## Problem

Phase 7 deferred identity because auth/session is route-adjacent (guards + sign-in pages) and risky to relocate behavior-preservingly. Architect validation (round 1) found the original single-ticket scope too large: the "auth" libs have 35+ importers across middleware/route handlers/most modules, and authenticated-fetch/server-fetch is the shared HTTP client (mis-classified as auth). Identity is therefore split: AE-0156 (this — auth-specific client lib) + AE-0164 (route handlers/guards), both gated on the AE-0165 auth e2e.

## Scope

Create modules/identity with a public barrel; move ONLY the auth-specific client logic (jwt-auth, auth-cookie, the login/session client surface) behind it; route consumers through @/modules/identity; leave re-export shims at the old lib/ auth paths so nothing breaks. The shared authenticated-fetch/server-fetch HTTP client STAYS in lib/. Verified byte-identical via the AE-0165 auth e2e + unit tests.

## Non-Goals

- No auth BEHAVIOR change (same tokens/cookies/guards/redirects).
- No App Router URL change; route handlers under app/api/auth + guards are AE-0164 (not this slice).
- authenticated-fetch / server-fetch (the app-wide HTTP client) are NOT moved (platform infra, not auth).

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] modules/identity SHALL own the auth-SPECIFIC client lib (jwt-auth, auth-cookie, login/session client) behind a public contract; consumers import @/modules/identity; re-export shims keep old lib/ auth paths resolving
- [ ] authenticated-fetch / server-fetch (app-wide HTTP client) SHALL remain in lib/ (NOT moved into identity)
- [ ] Auth behavior byte-identical; the AE-0165 auth e2e SHALL pass; App Router URLs unchanged
- [ ] typecheck + lint (boundary 0/0) + 822 unit tests + build + check:legacy green

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (back-end gates.sh + check-integrity + arch-ratchet; front-end typecheck/lint/boundaries/url/circular/tests/build).

## Dependencies

- Blocks: AE-0164
- Blocked by: AE-0153, AE-0165
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
