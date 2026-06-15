# AE-0102 — SSE streaming behind conversation via ChatAgentFactory (byte-identical SSE)

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0102-conversation-sse
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Move `chat_stream.py` SSE endpoints behind the conversation facade, with chat-agent construction via the AE-0100 `ChatAgentFactory` adapter. SSE event payloads, framing, keep-alive, Last-Event-ID, and X-Agent-Origin stay byte-identical; AlterEgo/RAG routing + knowledge retrieval unchanged.

## Problem

SSE streaming + agent construction couple routes to ChatStreamService and api/dependencies/agents.py. Phase 3 moves this behind conversation/application contracts (the agent factory) without changing the wire.

## Scope

- Both SSE endpoints (public alter-ego stream; auth carousel publish-chat stream) delegate via the conversation facade; agents built via the ChatAgentFactory adapter.
- Preserve SSE event types/order (token/sources/complete/error/tool_result), `id:`/`data:` framing, keep-alive ping cadence, Last-Event-ID resume, and the X-Agent-Origin header EXACTLY (SSE names already frozen, AE-0076).
- Keep metadata.project_id → AlterEgo/RAG routing and the Phase-2 knowledge-facade wiring identical.
- Conversation streaming app code imports no concrete Postgres repo / get_container.

## Non-Goals

- No SSE payload/name changes (AE-0076 frozen).
- No agent behavior change.

## Modularization Alignment (2026-06-15)

Phase 3 of the modularization plan (§Phase 3). **Behavior-preserving** — cookies (access_token/anon_token), HS256 JWT payloads, bcrypt, URLs, and SSE event payloads/keep-alive/Last-Event-ID/X-Agent-Origin stay byte-identical; NO renames (Phase 4+). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the Phase-2 `platform/database` UoW, the AE-0093 `KnowledgeSearchPort`, and the knowledge facade; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 2 (PR #16) merged. Gated on the AE-0097 SSE-stream snapshot diff=0 + agent retrieval tests passing.

## Acceptance Criteria

- [ ] BOTH SSE endpoints SHALL delegate via the conversation facade + ChatAgentFactory
- [ ] WHEN a chat stream runs (deterministic mock agent) THE SSE event TYPES in order + `id:`/`data:` framing FORMAT + Last-Event-ID + X-Agent-Origin SHALL match the AE-0097 SSE snapshot (type/format assertion, not raw-byte diff of LLM tokens; keep-alive interleaving ignored)
- [ ] THE AlterEgo/RAG routing (metadata.project_id) + knowledge retrieval behavior SHALL be unchanged (agent + stream tests green)
- [ ] THE conversation streaming application code SHALL NOT import a concrete Postgres repository or get_container
- [ ] WHEN gates.sh + mypy + lint-imports + pytest run THEY SHALL pass

## Gherkin Scenarios

```gherkin
Feature: SSE streaming unchanged behind the module

  Scenario: alter-ego stream event sequence preserved
    Given a conversation
    When POST /api/conversations/{id}/chat/stream runs via the facade
    Then the SSE event sequence + keep-alive match the AE-0097 snapshot byte-for-byte
```

## Delta

### ADDED

- conversation streaming handler

### MODIFIED

- api/routes/chat_stream.py (delegate via facade)
- api/dependencies/agents.py (ChatAgentFactory adapter)

### REMOVED

- None

## Affected Areas

- Backend: streaming handler + agent adapter
- Frontend: none
- Database: none
- API: unchanged SSE
- Tests: SSE + agent parity
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0103
- Blocked by: AE-0100 (facade + ChatAgentFactory); soft-after AE-0101 (both touch the conversation facade — serialized to avoid churn; may parallelize if file scopes stay disjoint)
- Related: AE-0093, AE-0076

## Implementation Plan

1. Add streaming handler behind the facade.
2. Build agents via ChatAgentFactory.
3. SSE framing/keep-alive identical; snapshot diff=0; agent tests green.

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
