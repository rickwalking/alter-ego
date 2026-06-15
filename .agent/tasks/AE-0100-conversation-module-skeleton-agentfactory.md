# AE-0100 — modules/conversation skeleton + facade + repo ports + ChatAgentFactory port

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0100-conversation-module
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Create `modules/conversation/` behind a facade; re-export `Conversation`/`Message` + their repository ports; define a `ChatAgentFactory` port so chat-agent construction becomes an adapter behind conversation/application contracts. Reuse the Phase-2 knowledge facade + platform UoW.

## Problem

ConversationService/ChatStreamService exist but routes construct them directly and agent construction lives in `api/dependencies/agents.py`. The module needs a facade + an agent-factory port before routes/streaming can delegate (AE-0101/0102).

## Scope

- Scaffold `modules/conversation/` per conventions; facade exposes conversation ops + the agent factory.
- Re-export `Conversation`/`Message` entities and `ConversationRepository`/`MessageRepository` ports (shims at legacy domain/protocols paths; callers unbroken).
- Define a `ChatAgentFactory` port (build the alter_ego/rag agent for a conversation behind a contract) that consumes the AE-0093 `KnowledgeSearchPort`; the concrete factory wraps the existing `build_alter_ego_agent`/`build_rag_agent` (no behavior change yet).
- Wire via bootstrap (manual DI; reuse platform UoW + knowledge facade).

## Non-Goals

- No routes/streaming moved (AE-0101/0102).
- No agent behavior change.
- No carousel extraction.

## Modularization Alignment (2026-06-15)

Phase 3 of the modularization plan (§Phase 3). **Behavior-preserving** — cookies (access_token/anon_token), HS256 JWT payloads, bcrypt, URLs, and SSE event payloads/keep-alive/Last-Event-ID/X-Agent-Origin stay byte-identical; NO renames (Phase 4+). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the Phase-2 `platform/database` UoW, the AE-0093 `KnowledgeSearchPort`, and the knowledge facade; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 2 (PR #16) merged. The ChatAgentFactory keeps the metadata.project_id → AlterEgo/RAG routing and the knowledge-facade wiring identical.

## Acceptance Criteria

- [ ] modules/conversation SHALL exist per conventions with public.py facade + bootstrap.py (manual DI)
- [ ] Conversation/Message + ConversationRepository/MessageRepository ports SHALL be re-exported (existing callers unbroken)
- [ ] WHEN lint-imports + pytest run after the shims THE existing callers of those ports SHALL still resolve (CI-verified; object-identity shims)
- [ ] A `ChatAgentFactory` port SHALL be defined and the concrete factory SHALL wrap existing agent construction with identical routing (metadata.project_id) + knowledge-facade wiring
- [ ] THE module SHALL reuse the platform/database UoW and the Phase-2 knowledge facade (no duplication)
- [ ] WHEN mypy/lint-imports/pytest run THEY SHALL pass; no behavior change (agent tests green)

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; no runtime behavior change (verified by the AE-0097 safety net).

## Delta

### ADDED

- modules/conversation/{domain,application,infrastructure,api}/, public.py, bootstrap.py, constants.py
- ChatAgentFactory port + concrete factory adapter

### MODIFIED

- domain/protocols/repositories.py (re-export shims for Conversation/Message repos)

### REMOVED

- None

## Affected Areas

- Backend: conversation module + agent factory
- Frontend: none
- Database: none
- API: none yet
- Tests: import/type + agent smoke
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0101, AE-0102, AE-0103
- Blocked by: none
- Related: AE-0093, AE-0081

## Implementation Plan

1. Scaffold modules/conversation.
2. Re-export entities/ports.
3. Define ChatAgentFactory + wrap existing builders.
4. Bootstrap wiring; mypy/lint-imports/pytest.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 3 breakdown).

Dev Complete (Wave A). Created modules/conversation: object-identity Conversation/Message + repo-port shims, ChatAgentFactory port + LegacyChatAgentFactory wrapping build_agent_for_conversation (identical project_id routing + knowledge-facade wiring), reuses platform UoW + existing ConversationService. repositories.py untouched. Gate spine 14 PASS/0 FAIL/3 SKIP(DB→CI), integrity 0 blockers, mypy/lint-imports green.

## Files Touched

backend/src/rag_backend/modules/conversation/** (+public.py/bootstrap.py/constants.py), tests/unit/modules/conversation/*, tests/features/conversation_module.feature

## Test Evidence

Pending.

## QA Report

Phase 3 Wave A batch QA — converged PASS in 2 independent rounds (0 findings). See `.agent/reports/phase-3-wave-a.qa.md`.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
