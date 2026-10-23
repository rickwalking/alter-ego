# AE-0529 — Only the site owner's conversations read personal knowledge

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

Personal knowledge is searchable only in conversations owned by the site owner (Pedro). Every other
conversation, whether of an anonymous visitor, an editor or another admin, reads public knowledge only.

## Problem

`AlterEgoAgent` searches with the namespace prefix `personal`, which `HybridRetriever._resolve_namespaces`
widens to `personal` + `public`, and its `list_documents` tool lists the `personal` documents. The same
agent serves anonymous visitors, so a visitor can read and list everything the owner marked Pessoal. The
Knowledge Base now lets the owner choose Pessoal or Público per document, and Pedro decided that the public
chat must read public knowledge only; this has to ship before his CV, bio and blog posts are uploaded as
Público.

## Scope

- `agents/chat_knowledge.py`: two scopes, owner (search `personal` + `public`, list both) and public
  (search and list `public` only), and `knowledge_scope_for(owner_id, site_owner_id)`. It returns the owner
  scope only when the conversation owner stored on the server is the configured site owner.
- The site owner is the existing `AUTOPILOT_OWNER_USER_ID` setting, already in the prod secrets and already
  used as "the owner" for cover assets. Unset or invalid fails closed to public only.
- The Alter-Ego agent (stream and messages routes), the carousel (RAG) agent and `/api/search` take their
  scope from the owner; an agent built without a scope reads public only.
- `HybridRetrieverWithRRF` resolves a missing namespace prefix to `public` alone, so a future caller that
  names no namespace fails closed.
- The Knowledge Base scope hint says the public chat reads only Público knowledge.

## Non-Goals

- No database or API contract change.
- No change to the `personal` prefix (still `personal` + `public`) or to the carousel/internal namespaces.

## Acceptance Criteria

- [x] Given an anonymous conversation, Then the search runs on `public` only and the list tool lists public
      documents only.
- [x] Given a conversation of the configured site owner, Then the search covers `personal` + `public` and the
      list tool lists both.
- [x] Given a conversation of an editor or of another admin, Then public only.
- [x] Given no (or an invalid) `AUTOPILOT_OWNER_USER_ID`, Then every conversation, the owner's included, is
      public only.
- [x] Given an agent built without a scope, Then public only.
- [x] Given the stream and messages routes, Then both pick the scope from the conversation owner.
- [x] Given the real retriever over an index with one personal and one public chunk, When the public agent
      searches and lists, Then only the public chunk and document come back.
- [x] Given a retrieval with no namespace prefix, Then only `public` is read.
- [x] Given `/api/search` and the carousel (RAG) chat, Then personal knowledge only for the site owner.

## Gherkin Scenarios

- `backend/tests/features/public_chat_public_knowledge_ae0529.feature`

## Affected Areas

- Backend: `agents/chat_knowledge.py` (new), `agents/alter_ego_agent.py`, `agents/rag_agent.py`,
  `application/tools/knowledge_base/list_documents.py`, `api/dependencies/agents.py`,
  `api/routes/chat_stream.py`, `api/routes/search.py`, `infrastructure/retrieval/hybrid_retriever.py`,
  `infrastructure/config/settings.py` (docstring).
- Frontend: the Knowledge Base scope hint (pt, en).
- Database: none. API: none (same routes, narrower results for non-owners).
- Tests: backend unit + integration, frontend hint test.

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

### 2026-10-23 (review)

Review of the PR applied: the owner scope now needs the conversation owner to be the configured site owner
(editors and other admins read public only, unset fails closed), a proof test over the real retriever and
an in-memory index, a missing prefix resolves to `public` only, and `/api/search` and the carousel chat take
the owner's scope.

## Files Touched

- backend: see Affected Areas; tests `test_alter_ego_knowledge_scope_ae0529.py`,
  `test_public_knowledge_proof_ae0529.py`, `test_rag_agent_knowledge_scope_ae0529.py`,
  `test_public_chat_knowledge_scope_ae0529.py`, `test_knowledge_search_owner_scope_ae0529.py`, builder seams
  in the chat / conversation tests, `tests/pinecone_index_fakes.py` (query support), feature,
  `docs/architecture/openapi.json`.
- frontend: `i18n/locales/{pt,en}.json` (`knowledge.scope.hint`), `document-scope-forms.test.tsx`.

## Test Evidence

Backend: scope unit (21 incl. parametrized), proof over the real retriever (3), RAG agent scope (6),
stream + messages route integration (10), `/api/search` integration (4); the chat/agent/search test files
green. Gates: `.agent/reports/AE-0529.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- 2026-10-23 — Pedro: personal knowledge is searchable ONLY in conversations owned by Pedro, the site owner.
  Every other signed-in user (editors, other admins) and every anonymous visitor gets public knowledge only.
- 2026-10-23 — The site owner is identified by the existing `AUTOPILOT_OWNER_USER_ID` (already Pedro's user
  id in prod, already used as the owner of cover assets) instead of a new setting; unset fails closed to
  public only.
- 2026-10-23 — A retrieval with no namespace prefix reads `public` only (fail closed). `/api/search` and the
  carousel chat, which named no prefix, now pass the owner's scope so Pedro keeps personal + public there.

## Blockers

None.
