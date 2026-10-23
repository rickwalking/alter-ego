# AE-0529 — The public chat reads public knowledge only

Status: In Development
Tier: T2
Priority: High
Type: Bug
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Branch: feat/ae-0529-public-chat-public-knowledge
Created: 2026-10-23
Updated: 2026-10-23

## Goal

An anonymous visitor's chat answers only from the owner's public knowledge, while the owner's own chat
(a conversation of a signed-in user) keeps reading personal and public knowledge.

## Problem

`AlterEgoAgent` searches with the namespace prefix `personal`, which `HybridRetriever._resolve_namespaces`
widens to `personal` + `public`, and its `list_documents` tool lists the `personal` documents. The same
agent serves anonymous visitors, so a visitor can read and list everything the owner marked Pessoal. The
Knowledge Base now lets the owner choose Pessoal or Público per document, and Pedro decided that the public
chat must read public knowledge only; this has to ship before his CV, bio and blog posts are uploaded as
Público.

## Scope

- The chat agent gets a knowledge scope: public (search the `public` namespace, list `public` documents) or
  owner (search `personal` + `public`, list `personal` + `public` documents).
- An anonymous conversation (`user_id` null) gets the public scope, on the streaming route and on the
  non-streaming conversation messages route; a conversation of a signed-in user gets the owner scope.
- The agent's default is the public scope, so a builder that forgets to choose never widens access.

## Non-Goals

- The carousel (RAG) agent and `/api/search` (signed-in only) are unchanged.
- No change to the hybrid retriever's namespace resolution.
- No database or API contract change.

## Acceptance Criteria

- [x] Given an anonymous conversation, When the visitor chats, Then the knowledge search runs on the `public`
      namespace only and the `list_documents` tool lists only public documents.
- [x] Given a conversation of a signed-in user, When the owner chats, Then the search covers `personal` and
      `public` and the list tool lists personal and public documents.
- [x] Given an AlterEgoAgent built without a scope, Then it reads public knowledge only.
- [x] Given the streaming route and the non-streaming messages route, Then both pick the scope from the
      conversation's owner (anonymous → public).

## Gherkin Scenarios

- `backend/tests/features/public_chat_public_knowledge_ae0529.feature`

## Affected Areas

- Backend: `agents/alter_ego_agent.py`, new `agents/alter_ego_knowledge.py`,
  `application/tools/knowledge_base/list_documents.py`, `api/dependencies/agents.py`,
  `api/routes/chat_stream.py`.
- Frontend: none (the Knowledge Base hint text changes with AE-0502).
- Database: none.
- API: none.
- Tests: backend unit + integration.

## Dependencies

- Blocked by: none.
- Blocks: AE-0503 (Pedro uploads his public CV, bio and blog posts).

## Progress Log

### 2026-10-23

Ticket written from Pedro's decision that the public chat reads public knowledge only. Confirmed in the
code: the agent asks for `personal`, the retriever widens it to both namespaces, and the list tool lists
personal documents to every visitor.

Implemented: `agents/alter_ego_knowledge.py` holds the two scopes (public, owner) and
`knowledge_scope_for(owner_id)`; the agent takes them through `AlterEgoKnowledge` (default public);
`build_alter_ego_agent` takes the scope, picked from the conversation's `user_id` by both chat routes. The
list tool filters by a set of scopes and reads up to 100 recent completed documents before listing 20, so
personal documents do not crowd the public ones out of an anonymous listing.

## Files Touched

- backend: `agents/alter_ego_knowledge.py` (new), `agents/alter_ego_agent.py`,
  `application/tools/knowledge_base/list_documents.py`, `api/dependencies/agents.py`,
  `api/routes/chat_stream.py`; tests (`test_alter_ego_knowledge_scope_ae0529.py`,
  `test_public_chat_knowledge_scope_ae0529.py`, builder seams in the chat / conversation tests),
  feature, `docs/architecture/openapi.json` (stream route description).

## Test Evidence

New unit (10) and integration (4) tests green; the 14 test files that build or patch the chat agent
(245 tests) green. Gates: `.agent/reports/AE-0529.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
