# AE-0089 — modules/knowledge skeleton + ports + public facade

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0089-knowledge-module-skeleton
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Create `modules/knowledge/` (domain/application/infrastructure/api) per the AE-0081 conventions with a single public facade; define the `KnowledgeDocument` aggregate + command/query objects; expose the five ports (repository, vector store, embedding, retriever, processor). Relocate/re-export the existing domain models + protocols into the module — behavior-preserving.

## Problem

Documents/search logic is spread across `application/services`, `domain/models`, `domain/protocols`, and `infrastructure/`. Phase 2 needs the module shell + facade + ports in place before routes/search move behind it.

## Scope

- Create `modules/knowledge/{domain,application,infrastructure,api}` + `public.py` facade + `bootstrap.py` + `constants.py` per `module-conventions.md`.
- Define `KnowledgeDocument` aggregate (from the existing `Document` entity) and typed command/query objects (ingest/create/list/get/status/delete/reprocess/search).
- Place the five ports (DocumentRepository, VectorStore, EmbeddingService, Retriever, DocumentProcessor) in the module domain (relocate from `domain/protocols`, or re-export, behind the facade).
- Expose the knowledge operations via `public.py`; wire construction in `bootstrap.py` (manual constructor injection — no `get_container()` in the module).
- No route/search behavior change yet (that is AE-0092/0093).

## Non-Goals

- No moving the HTTP routes yet (AE-0092/0093).
- No renames of public API/DB.
- No new behavior.

## Modularization Alignment (2026-06-15)

Phase 2 of the modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 2). **Behavior-preserving extraction** — `/api/documents` and `/api/search` stay byte-identical; NO renames (Phase 4+). Builds on Phase 1 (PR #15): follow `docs/architecture/module-conventions.md` (AE-0081) + `modules/_template/`; satisfy the AE-0082 import contracts; compose via `bootstrap/` (no `get_container()` in module application code). Risk-register F1-F4 are Phase 4+ and do not apply (additive only). Establishes the reusable template AE-0095 documents; ports stay Protocols (no ABCs) per backend/CLAUDE.md.

## Acceptance Criteria

- [ ] THE `modules/knowledge/` package SHALL exist with per-layer dirs, `public.py` facade, `bootstrap.py`, matching `module-conventions.md`
- [ ] THE `KnowledgeDocument` aggregate + typed command/query objects SHALL be defined (no `Any`)
- [ ] THE five ports SHALL be exposed via the module domain and reachable only through the facade for cross-module use
- [ ] THE facade SHALL expose ingest/create/list/get/status/delete/reprocess/search operations
- [ ] WHEN `MYPYPATH=src uv run mypy -p rag_backend` runs THE module SHALL type-check cleanly
- [ ] WHEN `uv run lint-imports` runs THE module SHALL satisfy the public-facade contract (no internal cross-module import)
- [ ] WHEN `uv run pytest` runs THE full suite SHALL pass (no behavior change)

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; no runtime behavior change (verified by the AE-0088 safety net).

## Delta

### ADDED

- modules/knowledge/{domain,application,infrastructure,api}/
- modules/knowledge/public.py
- modules/knowledge/bootstrap.py
- KnowledgeDocument aggregate + command/query objects

### MODIFIED

- domain/models/documents.py, domain/protocols/* (relocated/re-exported into the module)

### REMOVED

- None

## Affected Areas

- Backend: new knowledge module
- Frontend: none
- Database: none
- API: none yet
- Tests: module import/type smoke
- Docs: references module-conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0091, AE-0092, AE-0093, AE-0094, AE-0095
- Blocked by: none
- Related: AE-0081, AE-0090

## Implementation Plan

1. Scaffold modules/knowledge per the template.
2. Define KnowledgeDocument + commands/queries.
3. Relocate/expose ports; build the facade + bootstrap.
4. mypy + lint-imports + pytest.

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
