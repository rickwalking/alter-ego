# AE-0079 — Phase 1 epic: architecture scaffolding without moving behavior

Status: Ready
Tier: T3
Priority: High
Type: Epic
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: N/A (epic; sub-tickets carry branches)
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

Stand up the target module architecture as structure only — package roots, public-API conventions, enforced import boundaries (backend + frontend), a fresh-DB migration CI job, and architecture ratchets — with zero behavior change. Tracks AE-0080 through AE-0085.

## Problem

Phase 0 is complete (AE-0071-0078) and the delta skeptical review cleared Phase 1 to start. Phase 1 creates the boundaries Phases 2-8 fill; without it, module extraction has nowhere to land and no guard against new global-layer violations. Precondition: PR #14 (Phase 0) merged.

## Scope

- Track sub-tickets AE-0080 (package roots), AE-0081 (module conventions), AE-0082 (import contracts + baseline), AE-0083 (frontend boundary lint), AE-0084 (fresh-DB alembic CI), AE-0085 (architecture reports + ratchets) to Review.
- Enforce the phase exit gate across all sub-tickets.
- Execution order: Wave A {0080,0081,0083,0084} → Wave B {0082} → Wave C {0085}.

## Non-Goals

- No business-logic moves, schema changes, route changes, or write redirection (that is Phase 2+).
- No new bounded-context implementation (Phase 2 Knowledge pilot is next).

## Modularization Alignment (2026-06-12)

Phase 1 of the approved modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 1). Scaffolding only — **no behavior moves, no schema changes, no route changes, no write redirection** (plan exit gate). The migrate-in-place delta review cleared Phase 1 (`.agent/reports/domain-modularization.delta-review.md`); the 4 residual WARNs are pre-Phase-4 (`docs/architecture/phase-0-risk-register.md`) and do not apply here. Use glossary (AE-0071) context names and ADR-0009 conventions. This epic is the umbrella; see `docs/plans/phase-1-architecture-scaffolding.md`.

## Acceptance Criteria

- [ ] WHEN all of AE-0080-0085 reach Review with QA pass THE epic SHALL be considered complete
- [ ] WHEN the phase exit gate is evaluated THE existing backend+frontend tests SHALL pass and routes SHALL be byte-identical
- [ ] WHEN new code introduces a global-layer import violation THE CI ratchet (AE-0082/0085) SHALL fail it
- [ ] THE Import Linter wildcard exemptions SHALL be replaced by a generated baseline exception list (AE-0082)
- [ ] THE fresh-DB `alembic upgrade head` CI job SHALL be green (AE-0084)
- [ ] EVERY code-touching child (AE-0080, AE-0082, AE-0083) SHALL carry an explicit no-behavior-change AC (route-snapshot equality and/or unchanged test suite); the epic SHALL NOT close while any child lacks it

## Gherkin Scenarios

Not applicable — scaffolding/structure only; no runtime behavior change.

## Delta

### ADDED

- None

### MODIFIED

- None

### REMOVED

- None

## Affected Areas

- Backend: yes (roots, contracts)
- Frontend: yes (boundary lint)
- Database: none
- API: none (unchanged)
- Tests: yes (existing suite must stay green)
- Docs: yes (conventions + plan)
- Prompts/LLM: none
- Observability: none
- Deployment: no

## Dependencies

- Blocks: Phase 2 (Knowledge pilot) start
- Blocked by: PR #14 (Phase 0) merge
- Related: AE-0070 (Phase 0 epic)

## Implementation Plan

1. Drive Wave A/B/C per docs/plans/phase-1-architecture-scaffolding.md.
2. Run architect validate loop to promote sub-tickets to Ready.
3. Per-wave developer-skill + external QA loop, then release.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-12

Ticket created by planner (Phase 1 epic breakdown).

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
