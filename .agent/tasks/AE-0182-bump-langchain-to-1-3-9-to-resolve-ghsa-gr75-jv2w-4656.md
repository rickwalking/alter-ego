# AE-0182 — Bump langchain to 1.3.9 to resolve GHSA-gr75-jv2w-4656

Status: Intake
Tier: T2
Priority: High
Type: Security
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal

Resolve the HIGH-severity `pip-audit` finding so the backend `pip-audit` gate
returns to green.

## Problem

Kaizen learning K6 from the Phase 8 Class B QA wave. `pip-audit` flags
**langchain 1.2.15 — GHSA-gr75-jv2w-4656** (fixed in 1.3.9). It is a pre-existing
advisory unrelated to the Class B wave (which touched no dependencies), so it was
left out of scope and tracked here. The backend `pip-audit` gate currently fails
on this single advisory.

## Scope

- Bump `langchain` to `>=1.3.9` (and any peers the resolver requires) in
  `backend/pyproject.toml` + `uv.lock`.
- Verify the LangGraph/Deep Agents code paths still import and the backend test
  suite passes (langchain 1.2 → 1.3 is a minor bump; check for API changes).
- Confirm `pip-audit` exits 0.

## Non-Goals

- Not a broader dependency-refresh; scoped to clearing this advisory.

## Acceptance Criteria

- [ ] `langchain >= 1.3.9` pinned; `uv.lock` updated.
- [ ] `uv run pip-audit` exits 0 (no known vulns).
- [ ] Backend test suite + mypy + import-linter green; agent workflows unaffected.

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

### 2026-06-17 HH:mm

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
