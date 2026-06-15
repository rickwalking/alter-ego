# AE-0101 — Conversation routes (CRUD + non-streaming chat) behind handlers

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0101-conversation-routes
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Move `conversations.py` endpoints (create/list/get/messages/delete/generate-title/non-stream chat) behind conversation application handlers via the facade; routes become thin adapters. `anon_token` cookie + `X-Agent-Origin` header + response shapes byte-identical.

## Problem

Conversation routes construct the service + repos + agent builder directly. They must delegate to the AE-0100 facade with no behavior change.

## Scope

- Each /api/conversations endpoint delegates to a conversation handler via the facade.
- Conversation application code imports NO concrete Postgres repository (port + facade only).
- Preserve the anon_token Set-Cookie attributes, X-Agent-Origin header, rate limits, access checks (via shared resource_access), status codes, and response shapes EXACTLY.
- Writes commit via the platform UoW.

## Non-Goals

- No SSE streaming yet (AE-0102).
- No contract/cookie changes.

## Modularization Alignment (2026-06-15)

Phase 3 of the modularization plan (§Phase 3). **Behavior-preserving** — cookies (access_token/anon_token), HS256 JWT payloads, bcrypt, URLs, and SSE event payloads/keep-alive/Last-Event-ID/X-Agent-Origin stay byte-identical; NO renames (Phase 4+). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the Phase-2 `platform/database` UoW, the AE-0093 `KnowledgeSearchPort`, and the knowledge facade; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 2 (PR #16) merged. Gated on AE-0097 conversation snapshots (incl. anon_token cookie + X-Agent-Origin) diff=0.

## Acceptance Criteria

- [ ] EACH /api/conversations endpoint SHALL delegate via the conversation facade
- [ ] WHEN any /api/conversations endpoint is called THE response (incl. anon_token Set-Cookie + X-Agent-Origin) SHALL diff to ZERO against the AE-0097 snapshots
- [ ] THE conversation application code SHALL NOT import a concrete Postgres repository (port/facade only)
- [ ] Conversation write endpoints SHALL persist via the platform UoW
- [ ] WHEN gates.sh + mypy + lint-imports + pytest run THEY SHALL pass; AE-0097 safety net green

## Gherkin Scenarios

```gherkin
Feature: Conversation endpoints unchanged after extraction

  Scenario: anonymous create still sets anon_token
    Given an anonymous create request
    When POST /api/conversations runs through the handler
    Then the response + anon_token cookie diff to zero against the snapshot
```

## Delta

### ADDED

- conversation command/query handlers

### MODIFIED

- api/routes/conversations.py (thin adapters via facade)

### REMOVED

- None

## Affected Areas

- Backend: handlers + routes
- Frontend: none
- Database: none
- API: unchanged contract
- Tests: endpoint parity
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0102, AE-0103
- Blocked by: AE-0097, AE-0100
- Related: resource_access (shared)

## Implementation Plan

1. Add conversation handlers behind the facade.
2. Convert routes to delegate.
3. Writes via UoW; cookies/headers identical; snapshot diff=0.

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
