# AE-0112 — Editorial import contracts + exit gate + baseline ratchet + checkpoint-drain rule

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Backend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0112-editorial-import-contracts
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Add Import Linter contracts enforcing the editorial exit gate (application/domain isolation incl. no carousel ORM except the ACL; public-facade), ratchet the AE-0082 baseline down, encode the checkpoint-drain rule, and document editorial as a worked example. Mirrors AE-0103.

## Problem

The editorial boundary must be CI-enforced (building on AE-0095/0103) and the checkpoint-drain rule made explicit, or the god-row coupling will silently return.

## Scope

- Add contracts: editorial-application-isolation (application/domain forbidden from importing frameworks/get_container/infrastructure — incl. carousel ORM — except the ACL) + editorial-public-facade (cross-module callers use the facade only), generated via render_importlinter.
- Regenerate `.importlinter`; ratchet the AE-0082 baseline DOWN (api->infra / get_container) or hold; --check stays PASS.
- Encode the checkpoint-drain rule (no schema-modifying migration while a live checkpoint references the old shape) in the exit-gate docs/CI note.
- Update module-conventions.md §11 with editorial as a worked example; record the ACL-only carousel-ORM exception.

## Non-Goals

- No weakening of existing contracts. Any shared cross-cutting import (e.g. resource_access authz) follows the AE-0103 grandfathered-exception pattern (documented, not a gate hole).
- No behavior change (CI/docs only).

## Modularization Alignment (2026-06-15)

Phase 4 of the modularization plan (§Phase 4). **Behavior-preserving** — the carousel workflow API + SSE event names/framing/keep-alive/`Last-Event-ID`, artifact URLs, response schemas, LangGraph checkpoint identifiers + schemas, and `lock_version` optimistic-lock semantics stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 3 (PR #17) merged.

## Acceptance Criteria

- [ ] Import Linter contracts SHALL isolate editorial.application/domain (no frameworks/get_container/infrastructure, carousel ORM only via the ACL) and enforce the public facade; lint-imports KEEPS them
- [ ] THE editorial-application-isolation contract SHALL name `modules.editorial.infrastructure.legacy_carousel_acl` as the ONLY allowed carousel-ORM import path (explicit, documented exception in render_importlinter)
- [ ] WHEN new code violates either boundary THE contract SHALL fail (demonstrated, reverted)
- [ ] THE AE-0082 baseline/--check SHALL ratchet DOWN or hold and stay PASS
- [ ] THE checkpoint-drain rule SHALL be documented as an exit-gate criterion (no schema migration while a checkpoint references the old shape)
- [ ] module-conventions.md SHALL document editorial as a worked example; gates.sh + check-integrity + full suite green

## Gherkin Scenarios

Not applicable — CI/docs deliverable; falsifiability demonstrated by a reverted violation.

## Delta

### ADDED

- editorial contracts in scripts/metrics/import_baseline.py (render_importlinter); module-conventions.md §11

### MODIFIED

- backend/.importlinter (regenerated); scripts/metrics/import_baseline.py (baseline constants)

### REMOVED

- None

## Affected Areas

- Backend: editorial module
- Frontend: none
- Database: none (additive-only if any; no schema migration planned)
- API: none yet
- Tests: contract/behavior tests
- Docs: module-conventions §11
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0104 (closes epic)
- Blocked by: AE-0110, AE-0111
- Related: AE-0103, AE-0095, AE-0104

## Implementation Plan

1. Add the two contracts to render_importlinter; regenerate .importlinter.
2. Ratchet baseline; demonstrate+revert a violation.
3. Document §11 + checkpoint-drain rule.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 4 breakdown).

Dev Complete (Wave E). editorial-application-isolation + editorial-public-facade contracts (zero ignores; violations demonstrated+reverted); baseline ratcheted down api->infra 82→81; module-conventions §11 + checkpoint-drain rule. lint-imports 16/0, --check PASS, mypy 480, integrity 0 blockers.

## Files Touched

scripts/metrics/import_baseline.py (editorial contracts + api->infra baseline 82→81), backend/.importlinter (regenerated, 16 contracts), docs/architecture/module-conventions.md (§11)

## Test Evidence

Pending.

## QA Report

Phase 4 Wave E / exit-gate QA — converged PASS in 2 independent rounds (round 2 executed the inject+revert falsifiability check; 0 findings). See `.agent/reports/phase-4-wave-e.qa.md`.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
