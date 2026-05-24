# Plan: Migrate Chat from WebSocket to Server-Sent Events (SSE)

## Status: DRAFT — Awaiting approval before implementation

---

## 1. Issue Identification

### 1.1 Primary Issue: WebSocket Fails Through Cloudflare HTTP/2

| Aspect | Detail |
|--------|--------|
| **Symptom** | Browser WebSocket `wss://marinssolutions.com/ws/chat/{id}` fails with `404` or connection error |
| **Root cause** | Cloudflare Free/Pro plan forces HTTP/2 on all TLS connections. HTTP/2 uses RFC 8441 extended CONNECT for WebSockets, but Cloudflare does **not** convert this to HTTP/1.1 `Upgrade` for origin servers. The backend (FastAPI + nginx) expects traditional `Upgrade: websocket` handshake. |
| **Evidence** | Live `curl` tests: HTTP/1.1 → `101 Switching Protocols`; HTTP/2 → `404 Not Found` (confirmed with valid `anon_token`) |
| **Community confirmation** | Dokploy #4202, Tornado #2888, Cloudflared #1465 — all report identical symptoms |
| **Constraint** | Cloudflare Free plan **does not allow disabling HTTP/2** (product-tier restriction since 2015) |
| **Impact** | Chat feature completely non-functional for all users accessing via `marinssolutions.com` |

### 1.2 Secondary Issue: Publish Page 500 Through Cloudflare

| Aspect | Detail |
|--------|--------|
| **Symptom** | `GET /create/{id}/publish` returns `500` through Cloudflare; `200` when hitting nginx directly |
| **Root cause hypothesis** | Next.js `middleware.ts` reads `cookies()` API. Cloudflare injects headers (`CF-IPCountry`, `CF-IPCity`, `CF-Ray`) that may contain non-ASCII characters. Next.js #85631 confirms: non-ASCII header values crash middleware with `MIDDLEWARE_INVOCATION_FAILED`. The debug log incorrectly attributed this to "stale cache". |
| **Evidence** | `cf-cache-status: DYNAMIC`; `?nocache=1` still 500s; direct nginx always 200; Next.js error markup in response body |
| **Impact** | Users cannot reach publish page, so even if chat worked, they couldn't access it |

### 1.3 Tertiary Issue: Frontend Cookie/Subprotocol Mismatch

| Aspect | Detail |
|--------|--------|
| **Symptom** | Frontend hooks (`use-websocket-chat.ts`, `use-publish-chat.ts`) read `document.cookie` for `access_token` and `anon_token`, but both cookies are `HttpOnly`. JavaScript cannot read them. |
| **Current behavior** | `new WebSocket(url)` is called without subprotocol token. Backend falls back to `websocket.cookies`, which only works when the request reaches the backend (it doesn't, due to Issue 1.1). |
| **Impact** | Auth token never reaches backend via intended subprotocol mechanism |

---

## 2. Proposed Solution

### 2.1 Architectural Decision: Replace WebSocket with SSE

**Rationale:**
- SSE is a standard HTTP `GET` request returning `text/event-stream`. No `Upgrade` handshake required.
- Works natively over HTTP/1.1, HTTP/2, and HTTP/3 without protocol-specific negotiation.
- Auth is handled via standard cookies/headers — no subprotocol hack needed.
- The project **already has a working SSE implementation** for carousel streaming (`/api/carousels/{id}/stream`).
- Industry precedent: Slack, Facebook, and many SaaS products use SSE as fallback when WebSockets are blocked by proxies.

**Trade-offs:**

| WebSocket | SSE |
|-----------|-----|
| Bidirectional (client can send anytime) | Unidirectional (server→client only) |
| Requires `Upgrade` handshake | Standard HTTP GET |
| Broken through Cloudflare HTTP/2 | Works through Cloudflare HTTP/2 |
| Subprotocol hack for auth | Standard cookies/headers |
| Lower latency for bidirectional games | Slightly higher latency for chat (acceptable) |

**Mitigation for bidirectional limitation:**
- Client-to-server messages use existing `POST /api/conversations/{id}/chat` (already implemented, used by the SSE fallback in `use-websocket-chat.ts`).
- The SSE stream only handles server→client token streaming.
- This matches the actual chat flow: user sends one message → server streams back many tokens.

### 2.2 High-Level Flow (Post-Migration)

```
User types message
    │
    ▼
Frontend: POST /api/conversations/{id}/chat/stream
  Body: {"content": "hello"}
  Credentials: include (cookies sent automatically)
    │
    ▼
Backend: Validate auth via cookies (access_token or anon_token)
  Persist user message to DB
  Start agent.chat(stream=True)
    │
    ▼
Backend: StreamingResponse(text/event-stream)
  data: {"type": "token", "content": "H"}
  data: {"type": "token", "content": "i"}
  data: {"type": "sources", "sources": [...]}
  data: {"type": "complete"}
    │
    ▼
Frontend: EventSource receives events, appends tokens to UI
```

---

## 3. Complete Codebase Change Map

### 3.1 Backend Changes

#### File A: `backend/src/rag_backend/api/routes/conversations.py`
**Action:** Add new `POST /{conversation_id}/chat/stream` endpoint.

```
INSERT after line 344 (end of existing chat() function):

@router.post(
    "/{conversation_id}/chat/stream",
    responses={
        200: {"description": "SSE stream of chat tokens"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def chat_stream(
    conversation_id: UUID,
    body: ChatRequest,
    request: Request,
    _user: Annotated[User | None, Depends(get_optional_user)] = None,
    db: Annotated[AsyncSession, Depends(get_session)] = None,
) -> StreamingResponse:
    """Send a chat message and stream the response via SSE.

    Accessible to both authenticated users and anonymous visitors.
    """
```

**Logic to implement:**
1. Validate conversation exists
2. Enforce per-conversation message limit
3. Persist user message to DB and commit
4. Build agent for conversation
5. Return `StreamingResponse` with `media_type=MEDIA_TYPE_STREAM`
6. Generator yields SSE events:
   - `data: {"type": "token", "content": "..."}\n\n`
   - `data: {"type": "sources", "sources": [...]}\n\n`
   - `data: {"type": "complete"}\n\n`
   - `data: {"type": "error", "content": "..."}\n\n`
7. After stream ends, persist assistant message to DB and commit

#### File B: `backend/src/rag_backend/api/app.py`
**Action:** Remove debug logging (lines 241–253) added during incident response.

```
DELETE lines 241-253:
    # DEBUG: log auth state
    import logging
    logger = logging.getLogger("websocket_debug")
    logger.warning(...)
```

**Action:** Keep the WebSocket endpoint for now (backward compatibility), but document it as deprecated.

#### File C: `backend/src/rag_backend/api/constants.py`
**Action:** Verify `MEDIA_TYPE_STREAM` constant exists (used by carousel SSE). If not, add it.

#### File D: `backend/src/rag_backend/api/schemas.py` (or dedicated constants)
**Action:** Add SSE event type constants:
```python
SSE_EVENT_TOKEN = "token"
SSE_EVENT_SOURCES = "sources"
SSE_EVENT_COMPLETE = "complete"
SSE_EVENT_ERROR = "error"
SSE_EVENT_TOOL_RESULT = "tool_result"
```

#### File E: New test files
**Create:** `backend/tests/api/routes/test_conversations_sse.py`
**Create:** `backend/tests/features/chat_sse.feature`

### 3.2 Frontend Changes

#### File F: `frontend/src/features/chat/hooks/use-websocket-chat.ts`
**Action:** Replace WebSocket logic with EventSource.

**Current behavior:**
- Opens `WebSocket(baseWsUrl, [token])`
- Listens to `onopen`, `onmessage`, `onclose`, `onerror`
- Falls back to `fetchSseResponse` (non-streaming POST)

**New behavior:**
- **Send message:** `POST /api/conversations/{id}/chat/stream` with `credentials: "include"`
- **Receive stream:** `EventSource` connecting to the same endpoint
  - Wait — `EventSource` only supports `GET`. Cannot send body with `POST`.
  - **Solution:** Use `fetch` with `ReadableStream` reader for the POST response, or use a two-step approach.

**Two-Step SSE Approach (recommended):**
1. User sends message via `POST /api/conversations/{id}/chat` (existing endpoint, or new stream endpoint with POST)
2. Backend starts processing, but we need to receive tokens back...

**Alternative: Single POST with ReadableStream**
```javascript
const response = await fetch(`/api/conversations/${id}/chat/stream`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  credentials: "include",
  body: JSON.stringify({ content }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const chunk = decoder.decode(value);
  // Parse SSE lines from chunk
}
```

This is actually better than `EventSource` because:
- It supports `POST` with a body
- Same streaming semantics
- No `EventSource` auto-reconnect complexity
- Full control over connection lifecycle

**Decision:** Use `fetch` + `ReadableStream` + `TextDecoder` for POST-based SSE consumption.

#### File G: `frontend/src/features/publish/hooks/use-publish-chat.ts`
**Action:** Same refactor as File F — replace WebSocket with `fetch` + `ReadableStream`.

#### File H: `frontend/src/constants/publish-chat.ts`
**Action:** Update constants:
- Add `SSE_EVENT_TYPE_TOKEN`, `SSE_EVENT_TYPE_COMPLETE`, etc. (if not already present)
- The file already has `WS_MESSAGE_TYPE_*` constants — rename or add `SSE_*` variants

#### File I: New frontend test files
**Create:** `frontend/src/features/chat/hooks/use-sse-chat.test.ts`
**Create:** `frontend/src/features/publish/hooks/use-publish-sse-chat.test.ts`

### 3.3 Nginx Changes

#### File J: `nginx/nginx.conf` (and `nginx.conf.ssl`)
**Action:** Add location for the new SSE endpoint (if needed). Existing `/api/conversations/` location already handles this.

**Action:** Sanitize Cloudflare headers that may crash Next.js middleware.

```nginx
# Add inside the HTTPS server block, before location directives:
# Strip potentially non-ASCII Cloudflare geo headers
map $http_cf_ipcity $safe_cf_ipcity {
    default "";
    ~^[\x00-\x7F]+$ $http_cf_ipcity;
}
```

Or simpler: just hide them from the upstream:
```nginx
# In the / location (frontend proxy)
proxy_hide_header cf-ipcity;
proxy_hide_header cf-ipregion;
proxy_hide_header cf-iplongitude;
proxy_hide_header cf-iplatitude;
```

### 3.4 Documentation Changes

#### File K: `docs/cloudflare-ws-debug.md`
**Action:** Update with findings and resolution.

#### File L: `CLAUDE.md` (root)
**Action:** No changes needed unless architecture section mentions WebSocket specifically.

---

## 4. Gherkin Scenarios

### Feature: Chat via Server-Sent Events

**File:** `backend/tests/features/chat_sse.feature`

```gherkin
Feature: Streaming chat via Server-Sent Events
  As a user
  I want to send a chat message and receive a streamed response
  So that I can have a real-time conversation with the AI

  Background:
    Given the backend is running
    And a conversation exists with id "conv-123"

  # Happy path
  Scenario: Authenticated user streams chat response
    Given I am authenticated as user "alice"
    When I POST to "/api/conversations/conv-123/chat/stream" with body:
      """
      {"content": "What is RAG?"}
      """
    Then the response status is 200
    And the Content-Type is "text/event-stream"
    And I receive SSE events in order:
      | type   | content |
      | token  | "Retrieval" |
      | token  | "-Augmented" |
      | token  | " Generation" |
      | sources| [{"document_id":"doc1","content":"..."}] |
      | complete| "" |
    And the user message is persisted in the database
    And the assistant message is persisted in the database

  # Happy path — anonymous user
  Scenario: Anonymous user streams chat response with valid anon_token cookie
    Given I have a valid anon_token cookie for conversation "conv-123"
    When I POST to "/api/conversations/conv-123/chat/stream" with body:
      """
      {"content": "Hello"}
      """
    Then the response status is 200
    And the Content-Type is "text/event-stream"
    And I receive at least one token event

  # Edge case — empty message
  Scenario: User sends empty message
    Given I am authenticated
    When I POST to "/api/conversations/conv-123/chat/stream" with body:
      """
      {"content": ""}
      """
    Then the response status is 422

  # Edge case — conversation not found
  Scenario: User streams chat for non-existent conversation
    Given I am authenticated
    When I POST to "/api/conversations/00000000-0000-0000-0000-000000000000/chat/stream"
    Then the response status is 404

  # Edge case — rate limit
  Scenario: Anonymous user exceeds message limit
    Given I am anonymous
    And conversation "conv-123" has 20 messages
    When I POST to "/api/conversations/conv-123/chat/stream"
    Then the response status is 429

  # Edge case — unauthorized (no auth cookie)
  Scenario: Unauthenticated user without anon_token
    Given I have no auth cookies
    When I POST to "/api/conversations/conv-123/chat/stream"
    Then the response status is 401

  # Failure — agent error during stream
  Scenario: Agent throws error mid-stream
    Given I am authenticated
    And the agent is configured to fail after 2 tokens
    When I POST to "/api/conversations/conv-123/chat/stream"
    Then the response status is 200
    And I receive an error SSE event
    And the connection closes gracefully
```

### Feature: Publish Page Through Cloudflare

**File:** `frontend/tests/features/publish_page.feature`

```gherkin
Feature: Publish page loads through Cloudflare proxy
  As a user
  I want to access the publish page through Cloudflare
  So that I can preview and publish my carousel

  Scenario: Publish page loads without 500 error
    Given I navigate to "/create/{valid-id}/publish"
    When the request goes through Cloudflare
    Then the page loads successfully
    And the status code is 200
    And no Next.js error markup is present
```

---

## 5. Testing Strategy

### 5.1 Unit Tests (Backend)

| Test | Target | Coverage Goal |
|------|--------|---------------|
| `test_chat_stream_valid_auth` | `conversations.py::chat_stream` | 100% happy path |
| `test_chat_stream_anon_token` | `conversations.py::chat_stream` | Cookie-based auth |
| `test_chat_stream_unauthorized` | `conversations.py::chat_stream` | Missing auth |
| `test_chat_stream_conversation_not_found` | `conversations.py::chat_stream` | 404 path |
| `test_chat_stream_rate_limit` | `conversations.py::chat_stream` | 429 path |
| `test_chat_stream_agent_error` | `conversations.py::chat_stream` | Error mid-stream |
| `test_chat_stream_empty_message` | `conversations.py::chat_stream` | Validation |
| `test_sse_event_format` | SSE generator function | Event format correctness |
| `test_chat_stream_persists_messages` | `conversations.py::chat_stream` | DB write verification |

### 5.2 Unit Tests (Frontend)

| Test | Target | Coverage Goal |
|------|--------|---------------|
| `test_use_sse_chat_connects` | `use-sse-chat.ts` | Opens fetch stream |
| `test_use_sse_chat_receives_tokens` | `use-sse-chat.ts` | Token accumulation |
| `test_use_sse_chat_receives_sources` | `use-sse-chat.ts` | Sources update |
| `test_use_sse_chat_receives_complete` | `use-sse-chat.ts` | Streaming ends |
| `test_use_sse_chat_sends_message` | `use-sse-chat.ts` | POST with credentials |
| `test_use_sse_chat_error_handling` | `use-sse-chat.ts` | Network error / parse error |
| `test_use_publish_sse_chat` | `use-publish-sse-chat.ts` | Same as above for publish |

### 5.3 Integration Tests

| Test | Method |
|------|--------|
| End-to-end chat flow | Playwright: create conversation → send message → verify streamed response appears |
| SSE through Cloudflare | Playwright against production URL |
| Publish page 500 fix | Playwright: load publish page → verify 200 |

### 5.4 Mutation Testing Strategy

**Tool:** `mutmut` (Python) or `cosmic-ray` for backend; Stryker for frontend.

**Mutations to test:**
1. Remove `await db.commit()` after user message persist → should fail (message must be committed before stream)
2. Change `media_type` from `text/event-stream` to `application/json` → frontend should reject
3. Remove `"\n\n"` terminator from SSE yield → parser should fail
4. Remove error event yield in exception handler → client should hang
5. Change `credentials: "include"` to `"omit"` → auth should fail

---

## 6. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **SSE does not fix the actual Cloudflare issue** | Low | High | Live test with `curl` before merge. SSE is standard HTTP GET/POST — no handshake to fail. |
| **Publish page 500 is unrelated to headers** | Medium | High | If header sanitization doesn't fix it, investigate Next.js `cookies()` parsing of Cloudflare's `CF-Visitor` JSON header. |
| **Frontend fetch ReadableStream not supported in older browsers** | Low | Medium | `ReadableStream` is supported in all modern browsers since ~2016. No IE11 support needed. |
| **Performance: SSE over HTTP/2 has connection limit** | Low | Low | HTTP/2 multiplexes streams over a single connection. Default limit is 100 streams. One SSE stream per tab is well within limits. |
| **Agent error mid-stream leaves DB in inconsistent state** | Medium | Medium | User message is committed before stream starts. Assistant message is only persisted after successful stream completion. If stream errors, no partial assistant message is saved. |
| **Regression: existing WebSocket consumers break** | Low | High | Keep WebSocket endpoint active but deprecated. Remove in v2.0 after SSE is proven stable. |
| **Rate limiting on SSE endpoint** | Medium | Medium | Apply same `@limiter.limit("10/minute")` decorator as existing chat endpoint. |
| **Memory leak: generator doesn't close on client disconnect** | Medium | High | Use `asyncio.CancelledError` handling in generator. Test with abrupt connection close. |

---

## 7. Tasks to be Performed by the LLM

### Phase 1: Backend Implementation
1. **Add SSE event type constants** to `backend/src/rag_backend/api/constants.py`
2. **Implement `chat_stream` endpoint** in `backend/src/rag_backend/api/routes/conversations.py`
   - Reuse the agent streaming logic from `chat.py`
   - Follow the exact `StreamingResponse` pattern from `carousels/generation.py`
   - Yield properly formatted SSE events
3. **Remove debug logging** from `backend/src/rag_backend/api/app.py`
4. **Write backend unit tests** for the new endpoint
5. **Run backend test suite** (`uv run pytest`) and ensure 90%+ coverage
6. **Run type checker** (`uv run mypy src/`) — strict mode

### Phase 2: Frontend Implementation
7. **Create new hook** `frontend/src/features/chat/hooks/use-sse-chat.ts`
   - Use `fetch` + `ReadableStream` + `TextDecoder`
   - Parse SSE lines (`data: {...}\n\n`)
   - Maintain same interface as `use-websocket-chat.ts` for drop-in replacement
8. **Replace WebSocket hook in chat page** — update imports
9. **Replace WebSocket hook in publish page** — update imports
10. **Write frontend unit tests** for `use-sse-chat.ts`
11. **Run frontend test suite** (`npm run test`) and ensure 90%+ coverage
12. **Run type checker** (`npm run typecheck`)

### Phase 3: Infrastructure
13. **Update nginx config** to sanitize Cloudflare geo headers
14. **Test publish page** through Cloudflare after nginx change
15. **Rebuild and redeploy** Docker containers

### Phase 4: Verification
16. **Live test SSE chat** through `marinssolutions.com` in browser
17. **Live test publish page** through Cloudflare
18. **Verify no regression** on carousel SSE (existing functionality)
19. **Update debug log** `docs/cloudflare-ws-debug.md` with resolution

---

## 8. Research References

### SSE Best Practices (Sources Consulted)

1. **MDN — Using Server-Sent Events**
   - Event stream format: `data: {...}\n\n`
   - Named events via `event: name\n`
   - Keep-alive comments (`: comment\n`) every 15s for proxy compatibility
   - `withCredentials: true` for cookie-based auth
   - HTTP/2 removes the 6-connection-per-domain limit

2. **HTML Standard — Server-Sent Events (WHATWG)**
   - Reconnection behavior: browser auto-reconnects with exponential backoff
   - `Last-Event-ID` header for resuming streams
   - Connection fails permanently on non-200 status or wrong Content-Type
   - UTF-8 encoding is mandatory

3. **FastAPI — StreamingResponse**
   - `StreamingResponse(generator, media_type="text/event-stream")`
   - Generator must yield strings
   - FastAPI handles chunked transfer encoding automatically

4. **Community Issues (Cloudflare + WebSocket)**
   - Dokploy #4202: Disabling HTTP/2 in reverse proxy is the only fix when you control the proxy
   - Tornado #2888: Same symptoms, fixed by forcing HTTP/1.1
   - Cloudflared #1465: Even Cloudflare's own tunnel has WebSocket handshake issues

---

## 9. Rollback Plan

If SSE introduces unforeseen issues:

1. **Revert backend:** WebSocket endpoint is untouched — simply don't use the new SSE endpoint
2. **Revert frontend:** WebSocket hooks are renamed, not deleted initially. Can restore imports.
3. **Short-term workaround:** Use a separate subdomain `ws.marinssolutions.com` with DNS-only (gray cloud) in Cloudflare to bypass the proxy entirely for WebSocket connections.

---

## 10. Success Criteria

- [ ] `POST /api/conversations/{id}/chat/stream` returns `200` with `Content-Type: text/event-stream`
- [ ] Browser receives token events in real-time through Cloudflare
- [ ] Publish page loads with `200` through Cloudflare (no 500)
- [ ] Backend test coverage ≥ 90%
- [ ] Frontend test coverage ≥ 90%
- [ ] `mypy --strict` passes with zero errors
- [ ] `npm run typecheck` passes with zero errors
- [ ] Existing carousel SSE continues to work
- [ ] Debug logging removed from `app.py`

---

## 11. Open Questions

1. Should we keep the WebSocket endpoint permanently, or deprecate and remove it after SSE is stable?
2. Should the new endpoint be `/chat/stream` (POST) or `/chat` (GET with query params for EventSource compatibility)?
3. Do we need a `Last-Event-ID` mechanism for resuming interrupted streams?
4. Should we add `: heartbeat\n\n` keep-alive comments in the SSE stream every 15-30 seconds?

---

*Plan created: 2026-05-22*
*Awaiting approval before implementation*
