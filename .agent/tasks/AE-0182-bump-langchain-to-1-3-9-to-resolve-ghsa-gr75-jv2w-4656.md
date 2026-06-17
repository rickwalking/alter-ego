# AE-0182 — Bump langchain to 1.3.9 to resolve GHSA-gr75-jv2w-4656

Status: Done
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

- [x] `langchain >= 1.3.9` pinned; `uv.lock` updated.
- [x] `uv run pip-audit` exits 0 (no known vulns).
- [x] Backend test suite + mypy + import-linter green; agent workflows unaffected.

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

### 2026-06-17 — Resolved (bundled into the AE-0203 Phase-2 ci-gate PR #36)

The new `CI Gate` aggregator's `backend-gate` surfaced this exact pre-existing
HIGH advisory (langchain 1.2.15 → GHSA-gr75-jv2w-4656), blocking ci-gate from
going green. Per the ratchet invariant the fix is the up-ratchet (bump), not a
pip-audit ignore-list entry. Applied:

- `backend/pyproject.toml`: `langchain>=1.2.15` → `>=1.3.9`.
- Resolver conflict: langchain 1.3.9 → langgraph 1.2.5 → langgraph-sdk 0.4.2
  caps `websockets<16`, but the project pinned `websockets>=16.0` (a #27 Phase-8
  freshness bump, not a security pin; no direct websockets imports in the code).
  Relaxed to `websockets>=14,<16` → resolved to **15.0.1**.
- `uv.lock` updated: langchain 1.3.9, langchain-core 1.4.7, langgraph 1.2.5,
  langgraph-sdk 0.4.2, websockets 15.0.1.

Local verification: `gates.sh backend:pip-audit` = PASS; app + agents/prompts
import OK with env; 560 langgraph/agent/workflow/prompt unit tests pass. Full
backend suite + mutation verified by `backend-gate` in CI on PR #36.

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

Cleared the HIGH `pip-audit` advisory GHSA-gr75-jv2w-4656 by bumping
`langchain` 1.2.15 → 1.3.9 (uv.lock: langchain-core 1.4.7, langgraph 1.2.5,
langgraph-sdk 0.4.2). Resolver required relaxing `websockets>=16.0` → `>=14,<16`
(→ 15.0.1; transitive-only, no direct imports). Verified: `pip-audit` PASS,
560 agent/langgraph unit tests pass, full backend suite + mutation green via
`backend-gate` on PR #36. Bundled into PR #36 (merged) because the new `ci-gate`
required check was blocked until this advisory cleared.
