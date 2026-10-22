# AE-0488 — Chat: honest reply when the knowledge base has nothing, generic error, no dangling user turn

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Claude — /chat QA (AE-0486 follow-up), CHAT-01, CHAT-03 (backend), CHAT-04
Branch: fix/ae-0486-chat-errors
Created: 2026-10-22
Updated: 2026-10-22

## Goal

A question the knowledge base cannot answer gets an honest reply. Any other failure is logged on the server, the
visitor sees a plain "try again" message, and the failed question never gets answered by the next turn.

## Problem

Found by the /chat QA:

- CHAT-01: with 0 knowledge-base matches the Alter-Ego rephrased its search until LangGraph's recursion limit (25)
  and the stream failed with `GRAPH_RECURSION_LIMIT`. Nothing was logged: the service caught the exception and only
  sent it to the client.
- CHAT-03 (backend half): the SSE `error` event carried `Error processing message: <exception text>`, including the
  LangGraph docs URL.
- CHAT-04: the user message was saved before streaming and nothing answered it on failure, so the next turn's agent
  answered the previous (failed) question first.

## Scope

- The Alter-Ego search tool has a budget of 3 searches per turn (`SearchToolOptions.max_calls`); past it the tool
  tells the agent to answer with what it has. The agent loop runs with `recursion_limit=25`; when it is reached the
  visitor gets "I don't have that in my knowledge yet…" in their language (pt/en) and the server logs
  `alter_ego_step_limit_reached`.
- `stream_chat_response` logs `chat_stream_failed` (conversation id + error type, with the traceback), saves an
  apology assistant turn (never the partial reply) and sends a generic error event.

- Search logs carry the query's length and a short hash, never the visitor's words (added during review).

## Non-Goals

- The empty knowledge base itself (data; tracked separately).
- Localized error copy and Retry in the UI (separate /chat PR).

## Acceptance Criteria

- [x] Step limit → honest reply, in the visitor's language, logged as a warning.
- [x] The search tool stops after 3 searches per turn (carousel chat unchanged: no budget).
- [x] Any stream failure is logged server-side with the conversation id and error type.
- [x] The client error event is `Sorry, I couldn't answer that one. Please try again.` (no exception text, no URL).
- [x] The failed turn is closed by an apology assistant message; partial text is never saved.

## Repro Steps

1. With an empty knowledge base, ask the public chat "Who are you? Answer with one link."
2. Before: red banner with the LangGraph recursion message and docs URL; "hello" next gets the old question's answer.
   After: an honest "not in my knowledge yet" reply; "hello" gets a reply to "hello".

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 12:00

Failing tests first; fixed the tool budget, the step-limit fallback, the service logging, the generic message and the
apology turn. One existing unit test pinned the old behavior (exception text in the event, no assistant message) and
was updated, with the `Agent throws exception during token generation` scenario.

## Files Touched

- backend/src/rag_backend/agents/alter_ego_agent.py, chat_fallback.py (new), rag_agent.py (call sites)
- backend/src/rag_backend/application/tools/knowledge_base/search_documents.py, __init__.py
- backend/src/rag_backend/application/services/chat_stream_service.py
- backend/src/rag_backend/domain/constants/chat_stream.py
- backend/tests/features/chat_errors.feature (new), alter_ego_chat_sse.feature
- backend/tests/unit/agents/test_alter_ego_step_limit.py (new),
  backend/tests/unit/application/test_chat_stream_failures.py (new), test_chat_stream_service.py

## Test Evidence

Pending (local gates, mutation in CI).

## QA Report

Pending.

## Blockers

None.
