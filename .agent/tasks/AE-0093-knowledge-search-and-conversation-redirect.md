# AE-0093 — Move search behind module + redirect conversation/agent search via facade

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0093-search-facade
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Move `/api/search` behind a knowledge search query handler and redirect the agent search tool + conversation search to resolve through the knowledge public facade. `/api/search` and agent/search behavior stay unchanged.

## Problem

Search logic lives in routes + a retriever wired directly into agents via `build_search_documents_tool`. The plan requires search to run behind the module and conversation search to go through the knowledge facade.

## Scope

- Add a knowledge search query handler; `/api/search` (POST+GET) delegates via `public.py`; response byte-identical.
- Redirect `build_search_documents_tool` / agent retrieval to obtain search through the knowledge facade rather than a direct retriever wiring that bypasses the module.
- Keep hybrid-search semantics (RRF, namespaces, alpha/top_k) and agent behavior identical.
- No SQLAlchemy/Pinecone import in the knowledge application search path.

## Non-Goals

- No search ranking/behavior change.
- No agent prompt/behavior change.
- No renames.

## Modularization Alignment (2026-06-15)

Phase 2 of the modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 2). **Behavior-preserving extraction** — `/api/documents` and `/api/search` stay byte-identical; NO renames (Phase 4+). Builds on Phase 1 (PR #15): follow `docs/architecture/module-conventions.md` (AE-0081) + `modules/_template/`; satisfy the AE-0082 import contracts; compose via `bootstrap/` (no `get_container()` in module application code). Risk-register F1-F4 are Phase 4+ and do not apply (additive only). Covered by the AE-0088 search scenarios + existing agent tests; behavior identical is the gate.

## Acceptance Criteria

- [ ] WHEN /api/search (POST and GET) is called THE response SHALL diff to ZERO against the committed AE-0088 search snapshots
- [ ] THE alter_ego_agent / rag_agent retrieval tests SHALL pass unchanged after redirecting wiring through the facade
- [ ] THE agent search tool / conversation search SHALL resolve through the knowledge public facade (not a module-bypassing retriever wiring)
- [ ] WHEN an agent performs retrieval THE results + behavior SHALL be unchanged (agent tests + search Gherkin pass)
- [ ] THE knowledge application search path SHALL NOT import SQLAlchemy or Pinecone
- [ ] mypy strict + full suite green

## Gherkin Scenarios

```gherkin
Feature: Search unchanged behind the module

  Scenario: hybrid search returns the same ranked results
    Given an indexed corpus and a query
    When POST /api/search runs through the knowledge query handler
    Then the ranked results match the pre-refactor behavior
```

## Delta

### ADDED

- knowledge search query handler

### MODIFIED

- api/routes/search.py (delegate via facade)
- api/dependencies/agents.py (retriever/document-repo wiring for alter_ego/rag agents → resolve via knowledge facade)
- application/tools/knowledge_base/search_documents.py + agent wiring (resolve via facade)

### REMOVED

- None

## Affected Areas

- Backend: search handler + agent wiring
- Frontend: none
- Database: none
- API: unchanged
- Tests: search + agent parity
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0095
- Blocked by: AE-0088 (snapshot safety net), AE-0089, AE-0091
- Related: AE-0088

## Implementation Plan

1. Add search query handler; route /api/search via facade.
2. Redirect agent/conversation search through the facade.
3. Verify search + agent behavior identical.

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
