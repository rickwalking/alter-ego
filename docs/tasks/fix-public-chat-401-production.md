# TASK-003 — Fix Public Chat 401 in Production

Status: Resolved
Owner: agent
Branch: fix/public-chat-401-production
Created: 2026-06-02
Updated: 2026-06-02

## Goal

Fix the 401 Unauthorized error returned by the conversation endpoint in production for non-authenticated users. The public chat at `/chat` works locally but fails in production with a 401 error.

## Root Cause Investigation Summary

The investigation traced every code path across backend, frontend, nginx, and middleware:

### Backend Endpoints Used by Public Chat
| Endpoint | Auth | Returns 401? |
|----------|------|-------------|
| `POST /api/conversations` | `get_optional_user` | No (returns `None` for anonymous) |
| `POST /api/conversations/{id}/chat/stream` | None | No |

Both endpoints are correctly configured. The `get_optional_user` → `get_current_user_optional` → `decode_access_token` chain never raises 401 — it returns `None` for missing/expired tokens.

### Frontend API Flow
- `PublicChatView` → `useCreateConversation` → `apiCall("POST", "/api/conversations", ...)`
- `PublicChatView` → `useSseChat` → `streamSseEvents("POST", "/api/conversations/{id}/chat/stream", ...)`
- Both use relative URLs with `credentials: "include"`
- `apiCall` has a 401 redirect handler (`api-client.ts:60-68`) that redirects to `/api/auth/logout`

### Actual Root Cause

**Nginx trailing slash routing mismatch + 301 redirect method change.**

The frontend sent `POST /api/conversations` (no trailing slash). Nginx's `location /api/conversations/` (with trailing slash) did NOT match, so the request fell through to `location /api/`. The backend FastAPI redirected `/api/conversations` → `/api/conversations/`, but the redirect was returned as a **301** (not 307), causing the browser to convert POST → GET. The `GET /api/conversations/` hit the listing endpoint which requires auth → **401**.

### Suspected Root Causes (investigated and ruled out)

1. ~~Stale `access_token` cookie~~ — Ruled out: `get_optional_user` returns `None` for missing/expired tokens, never 401.
2. ~~Cloudflare WAF~~ — Ruled out: No WAF blocks on this endpoint.
3. ~~Missing `ARG NEXT_PUBLIC_API_URL`~~ — Fixed but unrelated to 401.

## Scope

- Identify and fix the 401 in production for the public chat
- Add diagnostic logging to the `create_conversation` endpoint
- Add the missing `ARG NEXT_PUBLIC_API_URL` to the frontend Dockerfile
- Add a backend test for the anonymous conversation creation flow
- Verify the fix in production

## Out of Scope

- Dashboard chat authentication (works correctly)
- Admin panel changes
- Cloudflare configuration (user needs to verify this)
- Rate limiting configuration

## Acceptance Criteria

- [x] Anonymous users can create conversations in production without 401
- [x] Anonymous users can send messages via SSE in production without 401
- [x] Diagnostic logging added to `create_conversation` for future debugging
- [x] Missing `ARG NEXT_PUBLIC_API_URL` added to frontend Dockerfile
- [x] Backend tests cover anonymous conversation creation
- [x] Existing tests still pass

## Plan

1. **Add diagnostic logging to create_conversation** — Log request origin, user presence, and any auth-related info
2. **Add ARG NEXT_PUBLIC_API_URL to frontend Dockerfile** — Fix the silently ignored build arg
3. **Add backend test for anonymous conversation** — Test `POST /api/conversations` without auth headers
4. **Verify in production** — Redeploy and test the public chat flow
5. **If 401 persists** — Add more detailed request tracing (log cookies, headers, rate limit counters)

## Progress Log

### 2026-06-02 — Investigation Complete

Traced all code paths. Backend code is correct — endpoints don't require auth. The 401 is most likely from:
- An environment configuration issue (different `SECRET_KEY` causing JWT decode issues, though it shouldn't 401)
- Cloudflare WAF intercepting the request
- A stale cookie from a previous session

### 2026-06-02 — Implementation Complete

- Added diagnostic logging to `create_conversation` (logs auth state, cookie keys, content-length)
- Added `ARG NEXT_PUBLIC_API_URL` to frontend Dockerfile
- Added unit tests for anonymous conversation creation (2 tests, both passing)
- All 849 backend tests pass
- Opened PR #6: https://github.com/rickwalking/alter-ego/pull/6

### 2026-06-02 — Production Verification Complete

- Identified actual root cause: nginx trailing slash mismatch causing 301 redirect → POST→GET conversion → 401
- Fixed by adding trailing slashes to `CONVERSATIONS` and `CONVERSATIONS_ALTER_EGO` endpoints in `frontend/src/constants/api.ts`
- Playwright MCP verified: `POST /api/conversations/` → 201, `POST /api/conversations/{id}/chat/stream` → 200
- Public chat now works for anonymous users in production

## Files Touched

- `backend/src/rag_backend/api/routes/conversations.py` — Add request logging
- `frontend/Dockerfile` — Add `ARG NEXT_PUBLIC_API_URL`
- `frontend/src/constants/api.ts` — Add trailing slashes to conversations endpoints
- `frontend/src/constants/api.test.ts` — Update test assertions
- `backend/tests/unit/api/test_conversations.py` — Add anonymous creation test

## Test Evidence

```bash
cd backend && uv run pytest tests/unit/api/test_conversations.py -v
cd frontend && npm run typecheck && npm run lint
```
