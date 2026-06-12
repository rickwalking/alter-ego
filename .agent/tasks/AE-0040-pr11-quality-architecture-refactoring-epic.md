# AE-0040 — PR #11 Code Quality and Architecture Refactoring (Epic)

Status: Intake
Tier: T3
Priority: High
Type: Epic
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0040-pr11-quality-refactoring
Kanban Card: AE-0040
Created: 2026-06-10
Updated: 2026-06-10

## Goal

Ship a systematic remediation of all 23 code review comments from PR #11 and 7 CI gate failures. Eliminate blanket ignores from `pyproject.toml`, install permanent CI guards, and refactor fragile architectural patterns (Builder, Strategy, Chain-of-Responsibility) where PR review explicitly requested them.

## Problem

PR #11 introduced ~227 Python files. Review found 23 code quality issues and 7 CI gate failures. Root cause: AI agents generated code without enforcing project rules (max-args=3, no magic strings, early returns, type safety), and blanket ignores hid violations. Without this epic, the codebase will continue accumulating technical debt.

## Scope

- 10 sub-tickets (AE-0041 through AE-0050) covering cleanup, architecture, CI
- Strategy/Builder/Chain-of-Responsibility patterns where PR comments explicitly requested them
- Deprecation wrappers for changed function signatures (1 sprint window)
- Gradual removal of `ignore_errors = true` and blanket ruff ignores
- CI mutation testing elevation from advisory to blocking

## Non-Goals

- Legacy pipeline removal (per ADR-007) — tracked separately
- New API endpoints or database schema changes
- Full migration to DeepAgents (per ADR-007) — tracked separately
- i18n changes beyond moving constants to dedicated files
- Custom Kanban web UI or auto-merge

## Acceptance Criteria

- [ ] All 10 sub-tickets created with full AC and Gherkin scenarios
- [ ] Execution order matches dependency graph (cleanup → architecture → CI → ignores)
- [ ] Deprecation wrappers defined for public function signature changes
- [ ] Rollback procedure documented for blanket ignore removal
- [ ] Mutation score targets specified per new code path
- [ ] `high_risk_areas` tagged on tickets T2+

## Gherkin Scenarios

```gherkin
Feature: Epic tracking

  Scenario: All tickets ready
    Given AE-0040 epic is in Planning
    When validate_all_tickets.py runs
    Then all AE-0041 through AE-0050 pass section validation
```

## Sub-Tickets

| ID | Title | Tier | Area |
|----|-------|------|------|
| AE-0041 | Magic Strings, Early Returns, Boolean Trap | T2 | Backend |
| AE-0042 | Null-Safety and Exception Suppression | T2 | Backend |
| AE-0043 | Segregate Overloaded Functions | T2 | Backend |
| AE-0044 | Builder Pattern for build_workflow_state_response | T2 | Backend |
| AE-0045 | Strategy and Chain-of-Responsibility for Presentation Logic | T2 | Backend |
| AE-0046 | Validation Refactor for ContentSlideCopy | T2 | Backend |
| AE-0047 | Frontend Modularization | T2 | Frontend |
| AE-0048 | Remove Blanket Ignores + Mypy Hardening | T3 | Backend/CI |
| AE-0049 | CI Gate Improvements | T2 | CI/DevOps |
| AE-0050 | Rollback, Migration, and Observability Safeguards | T2 | Cross-cutting |

## Dependencies

- Blocks: None
- Blocked by: None
- Related: PR #11, ADR-005, ADR-007, ADR-008

## Implementation Plan

See `docs/plans/ae-0040-pr11-quality-architecture-refactoring.md`.

## QA Checklist

- [ ] Security reviewed — no auth/permission changes
- [ ] Code quality reviewed — all blanket ignores removed
- [ ] Acceptance criteria validated — per sub-ticket
- [ ] Edge cases tested — per sub-ticket
- [ ] Orphan/unfinished code checked — deprecation wrappers verified

## Progress Log

### 2026-06-10

Epic created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- Per validation: execution order reversed from original PRD (cleanup first, ignores last)
- Per validation: dispatch table over full Strategy classes for repair script (AE-0045)
- Deprecation wrappers: 1 sprint window for all changed public function signatures

## Blockers

None.

## Final Summary

Pending.
