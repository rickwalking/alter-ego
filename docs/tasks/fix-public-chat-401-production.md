# TASK-003 — Fix Public Chat 401 in Production

Status: In Review
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

### Suspected Root Causes (in priority order)

1. **The `access_token` cookie from a previous authenticated session** triggers the `get_user_repo` dependency chain which opens a database session. If the database connection pool is exhausted or the session fails in production, it cascades. However, `get_optional_user` returns `None` even in this case.

2. **Nginx routing mismatch** — `location /api/conversations/` (with trailing slash) does NOT match `POST /api/conversations` (no trailing slash). The request falls through to `location /api/`. While this should still work, the rate limiting is different (`api` zone vs `chat_api` zone).

3. **Cloudflare interference** — WAF rules or security features might be intercepting API calls.

4. **Missing `ARG NEXT_PUBLIC_API_URL` in frontend Dockerfile** — The build arg is passed in `docker-compose.prod.yml` but silently ignored because there's no `ARG` declaration in the Dockerfile.

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

- [ ] Anonymous users can create conversations in production without 401
- [ ] Anonymous users can send messages via SSE in production without 401
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

## Files Touched

- `backend/src/rag_backend/api/routes/conversations.py` — Add request logging
- `frontend/Dockerfile` — Add `ARG NEXT_PUBLIC_API_URL`
- `backend/tests/unit/api/test_conversations.py` — Add anonymous creation test

## Test Evidence

```bash
cd backend && uv run pytest tests/unit/api/test_conversations.py -v
cd frontend && npm run typecheck && npm run lint
```
