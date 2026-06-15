# AE-0087 — Phase 2 epic: pilot the Knowledge module

Status: Ready
Tier: T3
Priority: High
Type: Epic
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: N/A (epic; sub-tickets carry branches)
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Extract documents + search into a real `modules/knowledge/` bounded context (domain/application/infrastructure/api behind a public facade) with a request-scoped Unit of Work, behavior-preserving, proving the reusable module template. Tracks AE-0088 through AE-0095.

## Problem

Phase 1 stood up the scaffolding (roots, conventions, import contracts). Phase 2 is the first real context extraction; the Knowledge domain is cohesive and its protocols already exist, so it exercises HTTP, persistence, vendor adapters, ports, and tests without touching the largest workflow.

## Scope

- Track sub-tickets: AE-0088 (Gherkin safety net), AE-0089 (module skeleton+ports+facade), AE-0090 (ORM full-field repair), AE-0091 (request-scoped UoW), AE-0092 (document handlers), AE-0093 (search + conversation redirect), AE-0094 (repository contract tests), AE-0095 (import contract + exit gate).
- Enforce the phase exit gate.
- Order: Wave A {0088,0089,0090} → B {0091} → C {0092,0094} → D {0093} → E {0095}.

## Non-Goals

- No renames of tables/columns/API (Phase 4+).
- No new product features.
- No extraction of other contexts.

## Modularization Alignment (2026-06-15)

Phase 2 of the modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 2). **Behavior-preserving extraction** — `/api/documents` and `/api/search` stay byte-identical; NO renames (Phase 4+). Builds on Phase 1 (PR #15): follow `docs/architecture/module-conventions.md` (AE-0081) + `modules/_template/`; satisfy the AE-0082 import contracts; compose via `bootstrap/` (no `get_container()` in module application code). Risk-register F1-F4 are Phase 4+ and do not apply (additive only). Precondition: Phase 1 (PR #15) merged.

## Acceptance Criteria

- [ ] WHEN all of AE-0088-0095 reach Review with QA pass THE epic SHALL be complete
- [ ] THE knowledge application layer SHALL NOT import SQLAlchemy, FastAPI, Pinecone, or the global container (AE-0095 contract)
- [ ] WHEN the document+search Gherkin safety net runs THE scenarios SHALL pass before and after the refactor
- [ ] WHEN /api/documents and /api/search are called THE responses SHALL diff to ZERO against the committed AE-0088 pre-refactor snapshots (enforceable byte-identical guarantee)
- [ ] THE module template SHALL be documented and reusable (proven by the knowledge module)

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; no runtime behavior change (verified by the AE-0088 safety net).

## Delta

### ADDED

- None

### MODIFIED

- None

### REMOVED

- None

## Affected Areas

- Backend: yes (new module)
- Frontend: none
- Database: additive columns (AE-0090)
- API: none (unchanged contracts)
- Tests: yes
- Docs: yes (template)
- Prompts/LLM: none
- Observability: none
- Deployment: no

## Dependencies

- Blocks: Phase 3 (Identity/Conversation) start
- Blocked by: Phase 1 (PR #15) merge
- Related: AE-0079 (Phase 1 epic)

## Implementation Plan

1. Drive Waves A-E per docs/plans/phase-2-knowledge-module.md.
2. Run architect validate loop to Ready.
3. Per-wave developer-skill + external QA loop; keep the safety net green throughout.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 2 breakdown).

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
