# AE-0103 — Identity + Conversation import contracts + exit gate + baseline ratchet

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0103-id-conv-exit-gate
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Add Import Linter contracts enforcing the Phase 3 exit gate for both modules (conversation app imports no concrete Postgres repo; identity persistence not accessed by unrelated routes; public-facade contracts), ratchet the baseline down, and document both modules as worked examples.

## Problem

The exit gate requires the new modules' boundaries to be CI-enforced (building on AE-0082/0095) and the pattern documented for the remaining phases.

## Scope

- Add contracts: `modules.conversation.application` forbidden from importing concrete Postgres repositories (and sqlalchemy/get_container); `modules.identity.application/domain` isolated from framework/vendor/container; identity persistence not importable by unrelated routes.
- Add public-facade contracts for identity + conversation (cross-module callers use the facade only).
- Regenerate the AE-0082 baseline so both modules ratchet DOWN (never up); `--check` stays PASS.
- Update `docs/architecture/module-conventions.md` with identity + conversation as worked examples.

## Non-Goals

- No weakening of existing contracts.
- No behavior change.

## Modularization Alignment (2026-06-15)

Phase 3 of the modularization plan (§Phase 3). **Behavior-preserving** — cookies (access_token/anon_token), HS256 JWT payloads, bcrypt, URLs, and SSE event payloads/keep-alive/Last-Event-ID/X-Agent-Origin stay byte-identical; NO renames (Phase 4+). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the Phase-2 `platform/database` UoW, the AE-0093 `KnowledgeSearchPort`, and the knowledge facade; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 2 (PR #16) merged. Caps Phase 3; preserves unmatched_ignore_imports_alerting robustness.

## Acceptance Criteria

- [ ] Import Linter contracts SHALL forbid conversation.application from importing concrete Postgres repos (and sqlalchemy/get_container) and SHALL isolate identity.application/domain; lint-imports KEEPS them
- [ ] Public-facade contracts for identity + conversation SHALL forbid cross-module imports of internals; demonstrated by a reverted violation
- [ ] WHEN new code violates either boundary THE contract SHALL fail (demonstrated, reverted)
- [ ] THE AE-0082 baseline/--check SHALL ratchet DOWN (get_container reduced) and stay PASS
- [ ] module-conventions.md SHALL document identity + conversation as worked examples; gates.sh + check-integrity + full suite green

## Gherkin Scenarios

```gherkin
Feature: Identity/Conversation boundaries enforced

  Scenario: conversation app importing a Postgres repo is blocked
    Given the conversation application layer
    When a new import of PostgresConversationRepository is added
    Then lint-imports fails the conversation contract
```

## Delta

### ADDED

- Import Linter contracts (identity + conversation)
- module-conventions worked examples

### MODIFIED

- backend/.importlinter
- scripts/metrics/import_baseline.py baseline
- docs/architecture/module-conventions.md

### REMOVED

- None

## Affected Areas

- Backend: import contracts
- Frontend: none
- Database: none
- API: none
- Tests: contract demos
- Docs: worked examples
- Prompts/LLM: none
- Observability: none
- Deployment: no

## Dependencies

- Blocks: none
- Blocked by: AE-0099, AE-0102
- Related: AE-0082, AE-0095

## Implementation Plan

1. Add identity + conversation boundary + facade contracts.
2. Ratchet baseline down; verify --check.
3. Document worked examples; demo violations.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 3 breakdown).

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
