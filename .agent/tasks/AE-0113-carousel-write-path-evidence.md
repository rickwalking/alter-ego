# AE-0113 — Carousel write-path authorization evidence + scaled-down rollback drill

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend/Tests
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0113-carousel-write-path-evidence
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Produce the ADR-0009 / roadmap Phase-4-exit-gate evidence that MUST be complete before any carousel write path is redirected (AE-0107): three-entry-point authorization contract tests (HTTP, agent-tool, worker) over the carousel workflow write paths, plus the scaled-down rollback drill (database restore + trace-correlated smoke comparison — not a full production drill, per the scaled-down + migrate-in-place track).

## Problem

ADR-0009 §"Phase 2.5 exit-gate parameterization" (lines 108-117) moved the full-track contingent items — three-entry-point authorization contract tests and the rollback drill — to the **Phase 4 exit gate**, mandatory before the first redirected carousel write path. Phase 2.5 was skipped, so this evidence does not yet exist; AE-0107 (single write owner) is exactly that first redirection and cannot proceed without it.

## Scope

- Authorization contract tests asserting the carousel workflow write paths enforce identical access control through ALL THREE entry points: HTTP route, agent-tool, and background worker.
- Scaled-down rollback drill: a database restore drill over the carousel workflow data + a trace-correlated smoke comparison (legacy behavior vs post-change), documented — NOT a full production-traffic rollback drill (scaled-down track, ADR-0009 §2).
- Record the evidence (test files + a short drill report under docs/architecture/ or .agent/reports/) so the epic exit gate can cite it.

## Non-Goals

- No full production-traffic rollback drill / parity alerting / mixed-version testing (explicitly out per the scaled-down track).
- No production code change beyond what the contract tests require to be reachable.

## Modularization Alignment (2026-06-15)

Phase 4 of the modularization plan (§Phase 4). **Behavior-preserving** — the carousel workflow API + SSE event names/framing/keep-alive/`Last-Event-ID`, artifact URLs, response schemas, LangGraph checkpoint identifiers + schemas, and `lock_version` optimistic-lock semantics stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 3 (PR #17) merged.

## Acceptance Criteria

- [ ] Authorization contract tests SHALL assert identical access control on the carousel workflow write paths through the HTTP, agent-tool, and worker entry points
- [ ] A scaled-down rollback drill (database restore + trace-correlated smoke comparison) SHALL be executed and documented
- [ ] THE drill report SHALL explicitly record the scaled-down scope (no full production-traffic drill) per ADR-0009 §2
- [ ] THE evidence SHALL be complete and citable by the epic exit gate BEFORE AE-0107 redirects any write path
- [ ] WHEN gates.sh + pytest run THE authorization contract tests SHALL pass

## Gherkin Scenarios

```gherkin
Feature: Carousel write-path authorization parity (representative)

  Scenario Outline: same authorization across entry points
    Given an unauthorized actor
    When a carousel workflow write is attempted via <entry_point>
    Then access is denied identically
    Examples: | entry_point | http | agent-tool | worker |
```

## Delta

### ADDED

- three-entry-point authorization contract tests (HTTP/agent-tool/worker)
- scaled-down rollback drill report (DB restore + trace-correlated smoke)

### MODIFIED

- None (evidence/tests; minimal reachability hooks only if required)

### REMOVED

- None

## Affected Areas

- Backend: carousel workflow write-path authorization
- Frontend: none
- Database: restore drill (no schema change)
- API: none
- Tests: authorization contract tests
- Docs: rollback drill report
- Prompts/LLM: none
- Observability: trace-correlated smoke comparison
- Deployment: none

## Dependencies

- Blocks: AE-0107
- Blocked by: None
- Related: AE-0104, ADR-0009

## Implementation Plan

1. Author authz contract tests for HTTP, agent-tool, and worker write entry points.
2. Run the scaled-down rollback drill (DB restore + trace-correlated smoke); write the report.
3. Confirm evidence complete before AE-0107 starts.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created during Phase 4 architect validation round 1 (resolves blocker F1).

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
