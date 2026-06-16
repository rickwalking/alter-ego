# AE-0146 — Suspense data-loading ADR + guide

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Docs
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0146-suspense-data-loading-adr-guide
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

PR #21 (Phase 7) review follow-up. Suspense data-loading ADR + guide.

## Problem

PR #21 review: the 'never useEffect for data fetching; use Server Components / TanStack Query / React 19 use()+Suspense' rule lacks an ADR + guide, so the pattern isn't authoritative for future work.

## Scope

Write an MADR ADR in docs/decisions/ (next NNNN) recording the Suspense/React-19 use()+Server-Components data-loading decision, plus a short guide in docs/guides/ with the canonical patterns (Server Component initial data, TanStack Query client, use()+Suspense, error/loading boundaries). Docs-only.

## Non-Goals

- No behavior change beyond the stated fix.
- No App Router URL changes; existing green gates stay green.
- No gate-gaming (no eslint-disable/@ts-ignore/.skip/lowered thresholds/baseline additions beyond a documented down-only ratchet).

## Modularization Alignment (2026-06-16)

PR #21 (Phase 7 frontend alignment) review fix. Behavior-preserving; holds the Phase 7 green-gate safety net
(typecheck + eslint + lint:boundaries 0 + url:check 26 + lint:circular 0 + Vitest 822 + check:legacy + prettier
format) and the boundary ratchet (down-only). See `docs/plans/phase-7-frontend-alignment.md`.

## Acceptance Criteria

- [ ] An MADR ADR (docs/decisions/NNNN-*.md, status accepted) SHALL record the Suspense data-loading decision
- [ ] A guide (docs/guides/*.md) SHALL document the canonical patterns + anti-patterns
- [ ] Root + frontend CLAUDE/ADR indexes updated if applicable; docs-only, no code change

## Gherkin Scenarios

Not applicable — lint/CI/docs/dependency fix; verified by the green-gate safety net.

## Dependencies

- Blocks: —
- Blocked by: AE-0134
- Related: AE-0142

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created from PR #21 review.

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
