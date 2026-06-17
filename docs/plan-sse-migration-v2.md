# Plan: Complete WebSocket-to-SSE Migration & Chat Endpoint Separation

> Status: Superseded — historical record

## Status: ✅ APPROVED — Adjustments applied. Implementation in progress.

---

## 1. Executive Summary

This plan documents a **complete refactor** to replace all WebSocket infrastructure with Server-Sent Events (SSE), while separating the two distinct chat use cases into dedicated endpoints. This is **not a backward-compatible migration** — all WebSocket code will be removed.

### 1.1 The Two Chat Types

| Aspect | Alter-Ego Chat (Public) | Publish Chat (Private) |
|--------|------------------------|----------------------|
| **Agent** | `AlterEgoAgent` | `RAGAgent` (with carousel tools) |
| **Context** | Pedro's personal knowledge base | Carousel project context |
| **Users** | Anyone (no auth required, ephemeral) | Authenticated users only |
| **Where** | `/chat` page | `/create/{id}/publish` page |
| **Current endpoint** | `POST /api/conversations/{id}/chat` (non-streaming, to be deleted) | WebSocket `/ws/chat/{id}` |
| **New endpoint** | `POST /api/conversations/{id}/chat/stream` | `POST /api/conversations/{id}/publish-chat/stream` |
| **Agent builder** | `build_alter_ego_agent()` | `build_rag_agent()` |
| **Metadata flag** | None (no `project_id`) | `project_id` in metadata |

### 1.2 Why Separate Endpoints?

1. **Security**: Publish chat exposes carousel editing tools. It must only be accessible to authenticated users on the publish page.
2. **Agent isolation**: The `build_agent_for_conversation()` helper already routes by metadata. Separate endpoints make this explicit and enforceable at the route level.
3. **Rate limiting**: Different limits apply (public chat is more restrictive for anonymous users).
4. **Clarity**: Two distinct use cases deserve distinct contracts.

---

## 2. Complete Codebase Change Map

### 2.1 Backend — Files to Create, Modify, Delete

#### DELETE: `backend/src/rag_backend/api/websocket/chat.py`
- **Reason**: Entire WebSocket handler. Replaced by SSE endpoints.
- **Lines to remove**: 175 lines

#### DELETE: `backend/src/rag_backend/api/websocket/__init__.py`
- **Reason**: Directory will be empty after chat.py removal.

#### DELETE: `backend/src/rag_backend/api/app.py` lines 220–283
- **Reason**: WebSocket endpoint `@app.websocket("/ws/chat/{conversation_id}")` and all auth logic inside it.
- **Also delete**: Debug logging lines 241–253 (lines 242-254 in 1-indexed)

#### MODIFY: `backend/src/rag_backend/api/routes/conversations.py`
- **Current lines**: 345 lines (close to 400-line limit)
- **Action**: Extract streaming logic to a new module. Remove the non-streaming `chat()` endpoint. Keep conversation CRUD endpoints.
- **Delete**: `chat()` function (lines 265–345) — replaced by streaming endpoints in new module.
- **New endpoints**: None added here; all streaming endpoints go in `chat_stream.py`.

#### CREATE: `backend/src/rag_backend/api/routes/chat_stream.py`
- **Purpose**: Dedicated module for SSE streaming endpoints. Keeps `conversations.py` under 400 lines.
- **Content**: Two endpoint functions with shared generator logic.
- **Pattern**: Follow the exact `StreamingResponse` pattern from `carousels/generation.py`.

#### CREATE: `backend/src/rag_backend/application/services/chat_stream_service.py`
- **Purpose**: Extract the streaming orchestration logic (DB persistence, agent streaming, error handling) into a testable service.
- **Following**: Clean Architecture — domain logic belongs in the application layer, not API routes.
- **Max lines**: 400

#### MODIFY: `backend/src/rag_backend/api/constants.py`
- **Add**: SSE event type constants, error messages, new endpoint path constants.

#### MODIFY: `backend/src/rag_backend/api/schemas.py`
- **Add**: `ChatStreamRequest` schema (same as `ChatRequest` but for streaming).

#### MODIFY: `backend/src/rag_backend/api/routes/__init__.py`
- **Add**: Import and register new `chat_stream` router.

#### MODIFY: `backend/src/rag_backend/api/app.py`
- **Remove**: WebSocket endpoint and debug logging.
- **Add**: Include new `chat_stream` router.

### 2.2 Frontend — Files to Create, Modify, Delete

#### DELETE: `frontend/src/features/chat/hooks/use-websocket-chat.ts`
- **Reason**: WebSocket-based hook. Unused in current codebase but exists as dead code.

#### DELETE: `frontend/src/features/publish/hooks/use-publish-chat.ts`
- **Reason**: WebSocket-based hook. Will be replaced by SSE-based hook.
- **Note**: The publish page's conversation creation, message display, and tool result handling logic will be preserved and moved to the new hook.

#### CREATE: `frontend/src/features/chat/hooks/use-sse-chat.ts`
- **Purpose**: SSE-based hook for the Alter-Ego public chat.
- **Interface**: Same as current `useSendMessage` + streaming state.
- **Pattern**: Uses `fetch` + `ReadableStream` + `TextDecoder` (POST-based SSE consumption).
- **Max lines**: 400

#### CREATE: `frontend/src/features/publish/hooks/use-publish-sse-chat.ts`
- **Purpose**: SSE-based hook for the private carousel agent chat on publish page.
- **Interface**: Same return type as old `usePublishChat` to minimize page changes.
- **Pattern**: Uses `fetch` + `ReadableStream` + `TextDecoder`.
- **Max lines**: 400

#### CREATE: `frontend/src/lib/sse-client.ts`
- **Purpose**: Shared SSE client utility for parsing `text/event-stream` responses.
- **Following DRY**: Both hooks use the same parsing logic.
- **Max lines**: 200

#### MODIFY: `frontend/src/features/chat/hooks/use-chat.ts`
- **Action**: Replace `sendConversationMessage` call with new SSE-based `sendConversationMessageStream`.
- **Change**: `useSendMessage` will now manage streaming state (`isStreaming`, `error`) instead of just mutation state.

#### MODIFY: `frontend/src/features/chat/queries.ts`
- **Action**: Add `sendConversationMessageStream` function.
- **Pattern**: Returns an async generator that yields parsed SSE events.

#### MODIFY: `frontend/src/constants/api.ts`
- **Add**: `CONVERSATION_CHAT_STREAM` and `CONVERSATION_PUBLISH_CHAT_STREAM` endpoint constants.

#### MODIFY: `frontend/src/constants/publish-chat.ts`
- **Action**: Replace WebSocket constants with SSE constants.
- **Rename**: `WS_PROTOCOL_*` → remove. `WS_MESSAGE_TYPE_*` → `SSE_EVENT_TYPE_*`.

#### MODIFY: `frontend/src/features/chat/components/chat-interface.tsx`
- **Action**: Update to use streaming state from new `useSendMessage`.
- **Pattern**: Same UI, but messages stream in token-by-token instead of appearing all at once.

#### MODIFY: `frontend/src/app/(create)/create/[id]/publish/page.tsx`
- **Action**: Update import from `usePublishChat` to `usePublishSseChat`.
- **No UI changes**: Hook interface remains the same.

#### MODIFY: `frontend/src/app/(create)/create/[id]/publish/page.test.tsx`
- **Action**: Update mock import paths.

### 2.3 Infrastructure

#### MODIFY: `nginx/nginx.conf` and `nginx/nginx.conf.ssl`
- **Delete**: Both `/ws/` and `/ws/chat/` location blocks.
- **Add**: `proxy_hide_header` directives for Cloudflare geo headers (`cf-ipcity`, `cf-ipregion`, `cf-iplongitude`, `cf-iplatitude`).

### 2.4 Documentation

#### MODIFY: `docs/cloudflare-ws-debug.md`
- **Update**: Mark as resolved. Reference this plan.

#### CREATE: `docs/architecture/sse-chat.md`
- **Purpose**: Document the new SSE chat architecture for future developers.

---

## 3. Detailed Technical Design

### 3.1 Backend: SSE Event Format

Following the HTML Standard (WHATWG) and MDN best practices:

```
data: {"type":"token","content":"H"}\n\n
data: {"type":"token","content":"i"}\n\n
data: {"type":"sources","sources":[{"document_id":"..."}]}\n\n
data: {"type":"tool_result","tool":"refine_carousel_copy","result":"..."}\n\n
data: {"type":"complete"}\n\n
```

**Named events**: We will NOT use named events (`event: name\n`). All events are standard `message` events with a `type` field in the JSON payload. This simplifies parsing and matches the existing WebSocket event structure.

**Event IDs (Last-Event-ID)**: Each SSE event includes an `id` field for resumability:
```
id: 1\ndata: {"type":"token","content":"H"}\n\n
id: 2\ndata: {"type":"token","content":"i"}\n\n
```
If the client detects a dropped connection, it can retry the POST request with a `Last-Event-ID` header. The server will regenerate the stream from that checkpoint if possible, or restart from the beginning.

**Keep-alive**: Every 15 seconds, yield `: ping\n\n` to prevent proxy timeouts.

**Error handling**: If an error occurs mid-stream, yield `data: {"type":"error","content":"..."}\n\n` and then the generator exits. The HTTP status remains 200 (SSE convention — the stream itself contains the error).

### 3.2 Backend: Rate Limiting & Connection Kill

When `@limiter.limit("10/minute")` is exceeded:
1. `slowapi` raises an exception BEFORE the endpoint body runs.
2. FastAPI returns `429 Too Many Requests`.
3. The client (fetch ReadableStream) receives a non-200 status.
4. The stream parser detects this and surfaces it as a connection error.

**No special "kill connection" logic is needed** — standard HTTP rate limiting naturally terminates the request before streaming begins.

For mid-stream rate limits (e.g., message count limit): The `_check_conversation_limit()` guard runs before the generator starts. If the limit is reached, a `429` is returned immediately. The stream never starts.

### 3.3 Frontend: POST-Based SSE Consumption

`EventSource` only supports `GET`. Our chat requires a `POST` with a JSON body (`{"content":"hello"}`). We use `fetch` with `ReadableStream`:

```typescript
const response = await fetch(endpoint, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  credentials: "include", // Sends cookies automatically
  body: JSON.stringify({ content }),
});

if (!response.ok) {
  throw new Error(`HTTP ${response.status}`);
}

const reader = response.body!.getReader();
const decoder = new TextDecoder();
let buffer = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value, { stream: true });

  // Parse complete SSE events from buffer
  const events = parseSseEvents(buffer);
  buffer = events.remainder;

  for (const event of events.parsed) {
    yield JSON.parse(event.data);
  }
}
```

**Why this is better than EventSource:**
- Supports `POST` with body
- Full control over connection lifecycle
- No auto-reconnect complexity
- Works with standard HTTP auth (cookies)
- Compatible with all HTTP versions (1.1, 2, 3)

### 3.4 Agent Routing

The existing `build_agent_for_conversation()` helper routes by metadata:

```python
CONVERSATION_METADATA_PROJECT_ID = "project_id"

def build_agent_for_conversation(conversation, db, container):
    if CONVERSATION_METADATA_PROJECT_ID in conversation.metadata:
        return build_rag_agent(db, container)  # Private carousel agent
    return build_alter_ego_agent(db, container)  # Public knowledge agent
```

With separate endpoints, this routing becomes explicit:
- `POST /chat/stream` → calls `build_alter_ego_agent()` directly
- `POST /publish-chat/stream` → calls `build_rag_agent()` directly

The metadata check becomes a **defense-in-depth** validation rather than the primary routing mechanism.

### 3.5 Auth & Authorization

| Endpoint | Auth Required | Auth Method |
|----------|---------------|-------------|
| `POST /conversations/{id}/chat/stream` | None | No auth; conversation is ephemeral |
| `POST /conversations/{id}/publish-chat/stream` | Required | Cookie: `access_token` only |

**Anonymous Alter-Ego chat**: No auth required. Each page refresh creates a fresh conversation. No cookies, no localStorage, no history. The conversation exists in the DB only for the lifetime of the stream, then becomes orphaned (cleanup job can be added later).

**Authenticated publish chat**: `access_token` cookie via standard `HttpOnly` cookies sent with `credentials: "include"`. Frontend never reads cookies from JavaScript.

---

## 4. Gherkin Scenarios (Complete)

### Feature: Alter-Ego Public Chat via SSE

**File:** `backend/tests/features/alter_ego_chat_sse.feature`

```gherkin
Feature: Alter-Ego Public Chat Streaming
  As an anonymous or authenticated user
  I want to chat with Pedro's Alter-Ego
  So that I can learn about his career, skills, and experience

  Background:
    Given the backend is running
    And a conversation exists with title "Test Chat"

  # Happy path — authenticated user
  Scenario: Authenticated user sends a message and receives streamed tokens
    Given I am authenticated as user "alice"
    When I POST to "/api/conversations/{conv-id}/chat/stream" with body:
      """
      {"content": "What is your favorite programming language?"}
      """
    Then the response status is 200
    And the Content-Type is "text/event-stream"
    And the Cache-Control is "no-cache"
    And I receive SSE events in order:
      | type   | field    | condition       |
      | token  | content  | non-empty string |
      | token  | content  | non-empty string |
      | sources| sources  | array of objects |
      | complete| -       | event received   |
    And the user message is persisted in the database
    And the assistant message is persisted with non-empty content
    And the assistant message sources are populated

  # Happy path — anonymous user (no auth)
  Scenario: Anonymous user streams chat without any auth
    Given I have no auth cookies
    When I POST to "/api/conversations/{conv-id}/chat/stream" with body:
      """
      {"content": "Hello"}
      """
    Then the response status is 200
    And I receive at least one token event
    And no auth cookie is set in the response

  # Edge case — empty message
  Scenario: User sends empty message
    Given I am authenticated
    When I POST to "/api/conversations/{conv-id}/chat/stream" with body:
      """
      {"content": ""}
      """
    Then the response status is 422
    And the response contains "content cannot be empty"

  # Edge case — conversation not found
  Scenario: Chat for non-existent conversation
    Given I am authenticated
    When I POST to "/api/conversations/00000000-0000-0000-0000-000000000000/chat/stream"
    Then the response status is 404

  # Edge case — rate limit (per-conversation message cap)
  Scenario: Anonymous user exceeds conversation message limit
    Given I am anonymous
    And I have sent 19 messages in the current ephemeral conversation
    When I POST to "/api/conversations/{conv-id}/chat/stream" with the 20th message
    Then the response status is 429
    And the response contains "Conversation limit reached"

  # Edge case — rate limit (slowapi per-minute)
  Scenario: User exceeds per-minute rate limit
    Given I am authenticated
    And I have sent 10 messages in the last minute
    When I POST to "/api/conversations/{conv-id}/chat/stream"
    Then the response status is 429
    And no SSE stream is started

  # Edge case — conversation exists but is ephemeral
  Scenario: Anonymous user refreshes page and old conversation is gone
    Given I am anonymous
    And I had a conversation "old-conv" from a previous page load
    When I navigate to "/chat" again
    Then a new conversation is created
    And I cannot access conversation "old-conv" messages
    And no "anon_token" cookie exists

  # Failure — agent error mid-stream
  Scenario: Agent throws exception during token generation
    Given I am authenticated
    And the agent is configured to fail after emitting 2 tokens
    When I POST to "/api/conversations/{conv-id}/chat/stream"
    Then the response status is 200
    And I receive exactly 2 token events
    And I receive an error event with non-empty content
    And the stream ends gracefully
    And no partial assistant message is persisted

  # Failure — database error during user message persist
  Scenario: Database unavailable when persisting user message
    Given I am authenticated
    And the database connection is severed
    When I POST to "/api/conversations/{conv-id}/chat/stream"
    Then the response status is 500 or 503
    And no SSE events are emitted
    And no assistant message is created

  # Persistence — user message committed before streaming
  Scenario: User message is available immediately after stream starts
    Given I am authenticated
    When I POST to "/api/conversations/{conv-id}/chat/stream"
    Then the first SSE event is received
    And when I query "/api/conversations/{conv-id}/messages"
    Then the user message appears in the history

  # Streaming behavior — keep-alive
  Scenario: Slow agent response does not disconnect
    Given I am authenticated
    And the agent takes 25 seconds to respond
    When I POST to "/api/conversations/{conv-id}/chat/stream"
    Then the connection remains open
    And keep-alive pings are received every 15 seconds
    And the first token arrives within 30 seconds
```

### Feature: Publish Chat (Private Carousel Agent) via SSE

**File:** `backend/tests/features/publish_chat_sse.feature`

```gherkin
Feature: Publish Page Carousel Agent Streaming
  As an authenticated user
  I want to chat with the carousel agent on the publish page
  So that I can refine carousel copy and content

  Background:
    Given the backend is running
    And I am authenticated as user "alice"
    And a carousel project exists with id "proj-123"
    And a conversation exists with metadata {"project_id": "proj-123"}

  # Happy path
  Scenario: Authenticated user refines carousel copy
    Given the conversation is linked to project "proj-123"
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream" with body:
      """
      {"content": "Make the caption shorter"}
      """
    Then the response status is 200
    And the Content-Type is "text/event-stream"
    And I receive SSE events in order:
      | type        | field   | condition      |
      | token       | content | non-empty      |
      | token       | content | non-empty      |
      | tool_result | tool    | "refine_carousel_copy" |
      | complete    | -       | event received |
    And the user message is persisted
    And the assistant message is persisted

  # Auth — anonymous user denied
  Scenario: Anonymous user attempts publish chat
    Given I have no auth cookies
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream"
    Then the response status is 401

  # Auth — wrong user
  Scenario: User tries to access another user's publish chat
    Given I am authenticated as user "bob"
    And the conversation belongs to user "alice"
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream"
    Then the response status is 403

  # Edge case — conversation has no project_id metadata
  Scenario: Publish chat for non-carousel conversation
    Given a conversation exists with no "project_id" metadata
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream"
    Then the response status is 400 or 404
    And the response contains "not a carousel conversation"

  # Tool result — carousel copy refinement
  Scenario: Carousel copy refinement triggers cache invalidation
    Given I am authenticated
    And the conversation is linked to project "proj-123"
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream" with:
      """
      {"content": "Refine the Instagram caption"}
      """
    Then I receive a tool_result event with tool "refine_carousel_copy"
    And the carousel project "proj-123" is updated in the database
    And the assistant message contains the refined copy

  # Tool result — image regeneration
  Scenario: Image regeneration tool is called
    Given I am authenticated
    And the conversation is linked to project "proj-123"
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream" with:
      """
      {"content": "Regenerate the hero image"}
      """
    Then I may receive a tool_result event with tool "regenerate_image"
    And the image is updated in the carousel project
```

### Feature: Publish Page Through Cloudflare (500 Fix)

**File:** `frontend/tests/features/publish_page_cloudflare.feature`

```gherkin
Feature: Publish Page Loads Through Cloudflare
  As a user
  I want to access the publish page through the Cloudflare proxy
  So that I can preview and publish my carousel

  Scenario: Publish page loads without 500 error
    Given I navigate to "/create/{valid-carousel-id}/publish"
    When the request is proxied through Cloudflare
    Then the page status is 200
    And no Next.js error markup is present
    And the page title is not "Internal Server Error"
    And the carousel preview is visible
```

---

## 5. Testing Strategy

### 5.1 Backend Unit Tests

**Test file:** `backend/tests/api/routes/test_chat_stream.py`

| Test name | What it tests |
|-----------|--------------|
| `test_alter_ego_stream_authenticated_user` | Happy path: auth user gets SSE stream with tokens, sources, complete |
| `test_alter_ego_stream_anonymous_user` | Anon user (no auth) gets stream, no cookie set |
| `test_alter_ego_stream_no_auth_required` | No cookies → 200 (anonymous allowed) |
| `test_alter_ego_stream_conversation_not_found` | Invalid UUID → 404 |
| `test_alter_ego_stream_empty_message` | Empty content → 422 |
| `test_alter_ego_stream_rate_limit_messages` | 20 messages → 429 |
| `test_alter_ego_stream_rate_limit_per_minute` | 10/min → 429 |
| `test_alter_ego_stream_agent_error_mid_stream` | Agent fails mid-stream → error event, no partial persist |
| `test_alter_ego_stream_db_error_persist_user` | DB error → 500, no stream |
| `test_alter_ego_stream_user_message_committed_before_tokens` | User message in DB before first token |
| `test_alter_ego_stream_assistant_message_after_complete` | Assistant message in DB after complete event |
| `test_alter_ego_stream_sse_format` | Events follow `data: {...}\n\n` format |
| `test_alter_ego_stream_content_type` | Response header is `text/event-stream` |
| `test_alter_ego_stream_uses_alter_ego_agent` | Mock agent builder, verify `build_alter_ego_agent` called |
| `test_publish_stream_authenticated_user` | Happy path with RAGAgent |
| `test_publish_stream_unauthenticated` | No auth → 401 |
| `test_publish_stream_wrong_user` | Different user → 403 |
| `test_publish_stream_no_project_id` | Conversation without metadata → 400 |
| `test_publish_stream_uses_rag_agent` | Mock agent builder, verify `build_rag_agent` called |
| `test_publish_stream_tool_result_event` | RAGAgent emits tool_result → event forwarded |
| `test_chat_stream_service_error_handling` | Service-level error → error event yielded |

**Test file:** `backend/tests/application/services/test_chat_stream_service.py`

| Test name | What it tests |
|-----------|--------------|
| `test_stream_chat_persists_user_message` | User message committed before stream |
| `test_stream_chat_yields_token_events` | Token chunks yielded as SSE data |
| `test_stream_chat_yields_sources_event` | Sources yielded after tokens |
| `test_stream_chat_yields_complete_event` | Complete yielded at end |
| `test_stream_chat_persists_assistant_message` | Assistant message committed after stream |
| `test_stream_chat_agent_error` | Agent exception → error event, no persist |
| `test_stream_chat_empty_content_guard` | Empty content raises before streaming |
| `test_stream_chat_sanitizes_non_json_results` | Non-serializable tool results are stringified |

### 5.2 Frontend Unit Tests

**Test file:** `frontend/src/lib/sse-client.test.ts`

| Test name | What it tests |
|-----------|--------------|
| `test_parse_single_sse_event` | Parses `data: {...}\n\n` correctly |
| `test_parse_multiple_sse_events` | Parses multiple events in one chunk |
| `test_parse_partial_event_buffering` | Buffers partial events across chunks |
| `test_parse_ignores_comments` | Ignores `: ping\n` lines |
| `test_parse_empty_lines` | Handles double newlines correctly |
| `test_parse_invalid_json` | Returns parse error event |

**Test file:** `frontend/src/features/chat/hooks/use-sse-chat.test.ts`

| Test name | What it tests |
|-----------|--------------|
| `test_send_message_opens_stream` | POST opens, reader created |
| `test_receives_token_events` | Token events append to assistant message |
| `test_receives_sources_event` | Sources update last message |
| `test_receives_complete_event` | Streaming stops, refs reset |
| `test_receives_error_event` | Error state set, streaming stops |
| `test_http_error_handling` | 429/500 → error state |
| `test_connection_close_cleanup` | Reader closed, abort controller signaled |
| `test_concurrent_send_prevention` | Second send blocked while streaming |
| `test_optimistic_user_message` | User message appears immediately |

**Test file:** `frontend/src/features/publish/hooks/use-publish-sse-chat.test.ts`

| Test name | What it tests |
|-----------|--------------|
| `test_creates_conversation_with_project_id` | Conversation created with metadata |
| `test_receives_tool_result_event` | Tool result invalidates carousel cache |
| `test_context_prefix_appended` | `(carousel project_id=...)` prefix sent |
| `test_invalid_conversation_reset` | 404/mismatch clears localStorage |

### 5.3 Mutation Testing

**Backend mutations to verify (using `mutmut`):**

| Mutation | Expected Test Failure |
|----------|----------------------|
| Remove `await db.commit()` after user message persist | `test_stream_chat_persists_user_message` fails |
| Remove `"\n\n"` terminator from SSE yield | `test_alter_ego_stream_sse_format` fails |
| Change `media_type` from `text/event-stream` to `application/json` | Frontend parse tests fail |
| Remove error event yield in exception handler | `test_stream_chat_agent_error` fails |
| Change `build_alter_ego_agent` to `build_rag_agent` in alter-ego endpoint | `test_alter_ego_stream_uses_alter_ego_agent` fails |
| Remove `credentials: "include"` from fetch | Auth tests fail (but this is frontend) |
| Remove conversation existence check | `test_alter_ego_stream_conversation_not_found` fails |
| Remove `_check_conversation_limit` call | `test_alter_ego_stream_rate_limit_messages` fails |

**Frontend mutations to verify (using Stryker):**

| Mutation | Expected Test Failure |
|----------|----------------------|
| Remove `decoder.decode()` call | `test_receives_token_events` fails |
| Change event type check from `"token"` to `"complete"` | Token tests fail |
| Remove `streamingContentRef.current = ""` on complete | Complete event tests fail |
| Remove `credentials: "include"` | Auth-related tests fail |
| Remove abort controller signal | Cleanup tests fail |

---

## 6. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **SSE does not work through Cloudflare** | Very Low | Critical | SSE is standard HTTP GET/POST. Cloudflare handles HTTP/2 multiplexed streams natively. Test with `curl` before merge. |
| **Publish page 500 is unrelated to headers** | Medium | High | If header sanitization fails, investigate `CF-Visitor` JSON header parsing in Next.js `cookies()` API. Add error boundary to publish page. |
| **Main chat UI breaks due to streaming state changes** | Medium | High | `chat-interface.tsx` currently uses `useMutation` state. We'll add `isStreaming` and `error` state from the new hook. The UI already has `isLoading` — streaming state maps cleanly. |
| **Memory leak: generator doesn't close on unmount** | Low | High | Use `AbortController` in frontend. Backend generator handles `asyncio.CancelledError` on client disconnect. Tests verify cleanup. |
| **Agent tool results break SSE parser** | Low | Medium | `_sanitize_chunk()` already handles non-JSON results. Reuse this logic in SSE formatter. Test with tool_result events. |
| **Two endpoints confuse future developers** | Medium | Medium | Document clearly in `docs/architecture/sse-chat.md`. Name endpoints descriptively (`chat/stream` vs `publish-chat/stream`). |
| **Performance: slower than WebSocket for high-frequency messages** | Low | Low | Chat is low-frequency (one message, many tokens). SSE overhead is negligible. HTTP/2 header compression reduces overhead. |
| **Orphaned anonymous conversations in DB** | Medium | Low | Anonymous conversations are created but never referenced after page refresh. Add a background cleanup job (out of scope for this refactor, but noted). |
| **Breaking change for API consumers** | Very Low | Medium | No external API consumers. The `POST /chat` non-streaming endpoint is fully removed. |
| **File exceeds 400 lines** | Medium | Medium | Extract service logic to `chat_stream_service.py`. Keep routes thin. |

---

## 7. LLM Task List

### Phase 1: Backend Foundation

**Task 1.1 — Add SSE constants**
- **File**: `backend/src/rag_backend/api/constants.py`
- **Following**: AGENTS.md "No magic strings" — extract all string literals to constants.
- **Add**:
  ```python
  SSE_EVENT_TOKEN = "token"
  SSE_EVENT_SOURCES = "sources"
  SSE_EVENT_COMPLETE = "complete"
  SSE_EVENT_ERROR = "error"
  SSE_EVENT_TOOL_RESULT = "tool_result"
  SSE_KEEP_ALIVE_INTERVAL_SECONDS = 15
  ERR_EMPTY_MESSAGE = "Message content cannot be empty"
  ERR_NOT_CAROUSEL_CONVERSATION = "Not a carousel conversation"
  ```

**Task 1.2 — Create chat stream service**
- **File**: `backend/src/rag_backend/application/services/chat_stream_service.py`
- **Following**: AGENTS.md Clean Architecture — domain logic in application layer, not API routes.
- **Following**: AGENTS.md "Early returns preferred" — guard clauses at top.
- **Max lines**: 400
- **Interface**:
  ```python
  async def stream_chat_response(
      conversation_id: UUID,
      content: str,
      db: AsyncSession,
      agent_builder: Callable[..., AgentType],
  ) -> AsyncIterator[dict[str, object]]:
      """Stream chat response as SSE-compatible events."""
  ```

**Task 1.3 — Create chat stream routes module**
- **File**: `backend/src/rag_backend/api/routes/chat_stream.py`
- **Following**: AGENTS.md "Max 400 lines per file" — thin routes, logic delegated to service.
- **Following**: AGENTS.md "All functions have explicit return types".
- **Two endpoints**:
  - `POST /conversations/{id}/chat/stream` → `build_alter_ego_agent`, optional auth
  - `POST /conversations/{id}/publish-chat/stream` → `build_rag_agent`, required auth

**Task 1.4 — Register new router in app.py**
- **File**: `backend/src/rag_backend/api/app.py`
- **Delete**: WebSocket endpoint (lines 220–283) and debug logging (lines 241–253)
- **Add**: `app.include_router(chat_stream.router, prefix="/api")`

**Task 1.5 — Register new router in routes __init__.py**
- **File**: `backend/src/rag_backend/api/routes/__init__.py`
- **Add**: Import and expose `chat_stream` router.

**Task 1.6 — Delete WebSocket infrastructure**
- **Delete**: `backend/src/rag_backend/api/websocket/chat.py`
- **Delete**: `backend/src/rag_backend/api/websocket/__init__.py` (if empty)
- **Following**: Complete refactor — no backward compatibility.

**Task 1.7 — Write backend unit tests**
- **Files**:
  - `backend/tests/api/routes/test_chat_stream.py`
  - `backend/tests/application/services/test_chat_stream_service.py`
  - `backend/tests/features/alter_ego_chat_sse.feature`
  - `backend/tests/features/publish_chat_sse.feature`
- **Following**: AGENTS.md "Gherkin-first approach" — `.feature` files before test code.
- **Following**: AGENTS.md "Test behavior, not implementation" — mock external dependencies.
- **Coverage target**: ≥ 90% branch coverage.

**Task 1.8 — Remove non-streaming chat endpoint from conversations.py**
- **File**: `backend/src/rag_backend/api/routes/conversations.py`
- **Action**: Delete `chat()` function (lines 265–345). This endpoint is fully replaced by streaming.

**Task 1.9 — Run backend quality checks**
```bash
uv run pytest --cov=rag_backend --cov-branch
uv run mypy --strict src/
uv run ruff check src/
```

### Phase 2: Frontend Foundation

**Task 2.1 — Create SSE client utility**
- **File**: `frontend/src/lib/sse-client.ts`
- **Following**: Frontend AGENTS.md "No magic strings" — extract constants.
- **Following**: Frontend AGENTS.md "Explicit return types" — all functions declare return types.
- **Max lines**: 200
- **Last-Event-ID support**: The generator tracks the last received event ID. If the connection drops and the caller retries, the `Last-Event-ID` header is included in the retry POST request.
- **Interface**:
  ```typescript
  export interface SseParseResult {
    events: SseEvent[];
    remainder: string;
    lastEventId: string | null;
  }

  export interface SseEvent {
    id?: string;
    data: string;
  }

  export function parseSseEvents(buffer: string, lastEventId?: string | null): SseParseResult;

  export async function* createSseStream(
    endpoint: string,
    body: object,
    options?: { signal?: AbortSignal; lastEventId?: string | null },
  ): AsyncGenerator<Record<string, unknown>, void, unknown>;
  ```

**Task 2.2 — Update API constants**
- **File**: `frontend/src/constants/api.ts`
- **Add**:
  ```typescript
  CONVERSATION_CHAT_STREAM: (id: string) => `/api/conversations/${id}/chat/stream`,
  CONVERSATION_PUBLISH_CHAT_STREAM: (id: string) => `/api/conversations/${id}/publish-chat/stream`,
  ```

**Task 2.3 — Update publish-chat constants**
- **File**: `frontend/src/constants/publish-chat.ts`
- **Delete**: `WS_PROTOCOL_SECURE`, `WS_PROTOCOL_INSECURE`
- **Rename**: `WS_MESSAGE_TYPE_*` → `SSE_EVENT_TYPE_*`
- **Following**: Frontend AGENTS.md "No magic strings".

**Task 2.4 — Create Alter-Ego SSE chat hook**
- **File**: `frontend/src/features/chat/hooks/use-sse-chat.ts`
- **Following**: Frontend AGENTS.md "Props interfaces" — define hook return interface.
- **Following**: Frontend AGENTS.md "Early returns".
- **Max lines**: 400
- **Anonymous behavior**: On mount, creates a fresh conversation via `POST /api/conversations/`. No localStorage, no cookies. On unmount/page refresh, the conversation ID is lost. No history is loaded.
- **Interface**:
  ```typescript
  export interface UseSseChatReturn {
    messages: Message[];
    isStreaming: boolean;
    sendMessage: (content: string) => Promise<void>;
    error: string | null;
  }
  ```

**Task 2.5 — Update main chat hooks**
- **File**: `frontend/src/features/chat/hooks/use-chat.ts`
- **Action**: Replace `sendConversationMessage` with SSE-based streaming.
- **Update**: `useSendMessage` returns `{ mutateAsync, isStreaming, error }`.

**Task 2.6 — Update chat queries**
- **File**: `frontend/src/features/chat/queries.ts`
- **Action**: Add `sendConversationMessageStream` function.
- **Pattern**: Uses `createSseStream` utility.

**Task 2.7 — Create Publish SSE chat hook**
- **File**: `frontend/src/features/publish/hooks/use-publish-sse-chat.ts`
- **Following**: Same patterns as Task 2.4.
- **Max lines**: 400
- **Authenticated behavior**: Creates conversation with `project_id` metadata. Stores conversation ID in `localStorage`. Loads message history on mount via `useConversationMessages`. History persists across refreshes.
- **Preserves**: Conversation creation logic, project_id metadata, tool result handling, context prefix.

**Task 2.8 — Update publish page**
- **File**: `frontend/src/app/(create)/create/[id]/publish/page.tsx`
- **Change**: Import from `use-publish-sse-chat` instead of `use-publish-chat`.

**Task 2.9 — Update chat interface component**
- **File**: `frontend/src/features/chat/components/chat-interface.tsx`
- **Action**: Adapt to streaming state from new `useSendMessage`.
- **Pattern**: Same UI, but messages stream in token-by-token.

**Task 2.10 — Delete WebSocket hooks**
- **Delete**: `frontend/src/features/chat/hooks/use-websocket-chat.ts`
- **Delete**: `frontend/src/features/publish/hooks/use-publish-chat.ts`

**Task 2.11 — Write frontend unit tests**
- **Files**:
  - `frontend/src/lib/sse-client.test.ts`
  - `frontend/src/features/chat/hooks/use-sse-chat.test.ts`
  - `frontend/src/features/publish/hooks/use-publish-sse-chat.test.ts`
- **Following**: Frontend AGENTS.md "Gherkin scenarios first".
- **Following**: Frontend AGENTS.md "Mock external dependencies with MSW".
- **Coverage target**: ≥ 90% branch coverage.

**Task 2.12 — Run frontend quality checks**
```bash
npm run test
npm run typecheck
npm run lint
```

### Phase 3: Infrastructure

**Task 3.1 — Update nginx config**
- **Files**: `nginx/nginx.conf`, `nginx/nginx.conf.ssl`
- **Delete**: `/ws/` and `/ws/chat/` location blocks.
- **Add**: Cloudflare header sanitization in frontend proxy location:
  ```nginx
  proxy_hide_header cf-ipcity;
  proxy_hide_header cf-ipregion;
  proxy_hide_header cf-iplongitude;
  proxy_hide_header cf-iplatitude;
  ```

**Task 3.2 — Rebuild Docker images**
```bash
docker compose -f docker-compose.prod.yml build backend frontend nginx
docker compose -f docker-compose.prod.yml up -d
```

### Phase 4: Verification

**Task 4.1 — Live test Alter-Ego SSE**
- Method: Browser DevTools Network tab
- URL: `https://marinssolutions.com/chat`
- Verify: POST `/api/conversations/{id}/chat/stream` returns `text/event-stream`
- Verify: Tokens appear one-by-one in the UI

**Task 4.2 — Live test Publish SSE**
- Method: Browser DevTools Network tab
- URL: `https://marinssolutions.com/create/{id}/publish`
- Verify: POST `/api/conversations/{id}/publish-chat/stream` returns `text/event-stream`
- Verify: Tool results trigger carousel cache invalidation

**Task 4.3 — Verify publish page 500 fix**
- Method: `curl -I https://marinssolutions.com/create/{id}/publish`
- Verify: Status `200`, no Next.js error markup

**Task 4.4 — Verify no regression**
- Carousel SSE stream still works (`/api/carousels/{id}/stream`)
- Non-streaming chat endpoint still works (if kept temporarily)
- Auth flows unaffected

**Task 4.5 — Mutation testing**
- **Backend**: `mutmut run --paths-to-mutate=rag_backend/api/routes/chat_stream.py`
- **Frontend**: `npx stryker run`
- **Target**: All injected mutations must be caught by at least one test.

**Task 4.6 — Update documentation**
- **File**: `docs/cloudflare-ws-debug.md` → mark as resolved.
- **File**: `docs/architecture/sse-chat.md` → document new architecture.

---

## 8. Code Quality Guardrails (AGENTS.md / CLAUDE.md Compliance)

### Backend (from `backend/AGENTS.md`)

| Rule | How we enforce |
|------|---------------|
| **mypy strict mode** | `uv run mypy --strict src/` must pass before merge |
| **No explicit `Any`** | All dictionaries typed with `dict[str, object]` or `TypedDict`. Cast when necessary. |
| **No bare generics** | `dict[str, object]`, `list[dict[str, object]]`, `AsyncIterator[str]` |
| **Protocol for interfaces** | `ChatStreamService` defined as Protocol if needed for DI |
| **Explicit return types** | Every function declares return type |
| **Early returns** | Guard clauses: `if not conversation: raise HTTPException(...)` |
| **Max 400 lines** | `chat_stream.py` thin routes → `chat_stream_service.py` for logic |
| **Constants in dedicated files** | All SSE strings in `api/constants.py` |
| **Gherkin first** | `.feature` files written before test code |
| **90%+ branch coverage** | `pytest --cov-branch` |

### Frontend (from `frontend/AGENTS.md`)

| Rule | How we enforce |
|------|---------------|
| **TypeScript strict mode** | `npm run typecheck` must pass |
| **No `any` or `object`** | Use `Record<string, unknown>` or explicit interfaces |
| **Explicit return types** | All hooks and functions declare return types |
| **Props interfaces** | Every component has defined props interface |
| **No magic strings** | All SSE event types in `constants/publish-chat.ts` |
| **No hardcoded text** | All user-facing text via `useTranslations` |
| **i18n keys** | Translation keys follow `feature.component.key` pattern |
| **90%+ branch coverage** | `npm run test -- --coverage` |
| **MSW for external deps** | Mock `fetch` and EventSource in tests |

---

## 9. Architecture Decision Records

### ADR 1: POST-based SSE over EventSource

**Context**: `EventSource` only supports `GET` requests. Our chat requires a JSON body.

**Decision**: Use `fetch` + `ReadableStream` + `TextDecoder` for POST-based SSE consumption.

**Consequences**:
- (+) Supports `POST` with body, `credentials: "include"`, custom headers
- (+) Full control over connection lifecycle
- (+) No auto-reconnect complexity
- (-) Manual parsing of SSE chunks (mitigated by shared `sse-client.ts` utility)
- (-) No built-in `Last-Event-ID` for resuming (not needed for chat — each message is independent)

### ADR 2: Separate Endpoints for Alter-Ego vs Publish Chat

**Context**: Two distinct agents with different security requirements.

**Decision**: Two endpoints (`/chat/stream` and `/publish-chat/stream`) instead of one endpoint with metadata-based routing.

**Consequences**:
- (+) Explicit security: publish chat requires auth at route level
- (+) Clearer API contract for consumers
- (+) Independent rate limits possible
- (-) Slightly more code duplication (mitigated by shared `chat_stream_service.py`)

### ADR 3: Complete Removal of WebSocket Code

**Context**: User explicitly requested "fully replace" with no backward compatibility.

**Decision**: Delete all WebSocket files, endpoints, and hooks. No deprecation period.

**Consequences**:
- (+) Clean codebase, no dead code
- (+) No confusion for future developers
- (-) Cannot easily revert if SSE has issues (mitigated by thorough testing before merge)

### ADR 4: Anonymous Alter-Ego Chat is Ephemeral

**Context**: User requested anonymous conversations to be removed on page refresh entirely.

**Decision**: No `anon_token` cookie for Alter-Ego chat. Each page load creates a fresh conversation via `POST /api/conversations/`. No history, no localStorage, no persistence across refreshes.

**Consequences**:
- (+) True ephemeral experience for anonymous users
- (+) No cookie complexity for public chat
- (-) Orphaned conversations accumulate in DB (mitigated by a cleanup job, out of scope for this refactor)
- (-) Anonymous users lose context on refresh (acceptable per user requirement)

### ADR 5: Last-Event-ID for Stream Resumability

**Context**: User requested `Last-Event-ID` support for SSE streams.

**Decision**: Each SSE event includes an `id` field. The client tracks the last received ID. If the connection drops, the retry POST request includes `Last-Event-ID` header. The server attempts to resume from that checkpoint.

**Consequences**:
- (+) Follows HTML Standard for SSE
- (+) Improves resilience for slow or unreliable connections
- (-) Server must track event sequence or regenerate from checkpoint
- (-) For token streams, resuming mid-message is complex — the server may restart from the beginning of the current message

---

## 10. Rollback Plan (If Needed)

Since this is a complete refactor with no backward compatibility, rollback requires reverting the git commit. Before merge:

1. Create a feature branch: `git checkout -b refactor/sse-chat`
2. All changes isolated to this branch
3. Deploy to staging environment for live testing
4. Only merge after all 8 success criteria are met

**Emergency workaround** (if SSE fails in production):
- Create a subdomain `ws.marinssolutions.com` with DNS-only (gray cloud) in Cloudflare
- This bypasses Cloudflare proxy entirely
- Requires separate SSL certificate management
- Not ideal, but would restore WebSocket functionality instantly

---

## 11. Success Criteria

- [ ] `POST /api/conversations/{id}/chat/stream` returns `200` with `Content-Type: text/event-stream`
- [ ] `POST /api/conversations/{id}/publish-chat/stream` returns `200` with `Content-Type: text/event-stream`
- [ ] Alter-Ego chat streams tokens in real-time through Cloudflare
- [ ] Publish chat streams tokens and tool results through Cloudflare
- [ ] Publish page loads with `200` through Cloudflare (no 500)
- [ ] All WebSocket files deleted from codebase
- [ ] Debug logging removed from `app.py`
- [ ] Backend test coverage ≥ 90% (branch)
- [ ] Frontend test coverage ≥ 90% (branch)
- [ ] Backend mutation test score: 100% of mutations caught
- [ ] Frontend mutation test score: 100% of mutations caught
- [ ] `mypy --strict` passes with zero errors
- [ ] `npm run typecheck` passes with zero errors
- [ ] `ruff check src/` passes with zero warnings
- [ ] `npm run lint` passes with zero warnings
- [ ] Existing carousel SSE continues to work (regression test)
- [ ] Auth cookies work without JavaScript cookie reading (publish chat only)
- [ ] Anonymous Alter-Ego chat requires no auth and creates fresh conversation on each page load
- [ ] Rate limiting returns 429 before stream starts
- [ ] Agent errors mid-stream yield error event and close gracefully
- [ ] `Last-Event-ID` header supported on retry requests
- [ ] Documentation updated: `docs/cloudflare-ws-debug.md` marked resolved

---

## 12. User Decisions (Applied)

1. ✅ **Remove non-streaming `POST /chat` endpoint entirely.** The main chat UI will stream exclusively. Applied.

2. ✅ **Add `Last-Event-ID` support.** Each SSE event includes an `id` field. The client includes `Last-Event-ID` header on retry POST requests. Server regenerates stream from checkpoint. Applied.

3. ✅ **Anonymous Alter-Ego chat is fully ephemeral.** No `anon_token` cookie, no localStorage, no history. Conversation is created fresh on each page load and lost on refresh. Authenticated publish chat conversations persist in `localStorage` with history. Applied.

4. ✅ **Conversation ownership check for publish chat:** Yes, enforce 403 for wrong user. Applied.

---

## 13. Implementation Approved

**Status**: ✅ APPROVED — All adjustments applied. Ready for Phase 1 execution.

**Next step**: Execute Task 1.1 through Task 4.6 in order.

---

*Plan created: 2026-05-22*
*Based on: live endpoint testing, Cloudflare community research, MDN SSE docs, WHATWG HTML Standard, FastAPI StreamingResponse patterns, AGENTS.md, CLAUDE.md*
*Awaiting approval before implementation*
