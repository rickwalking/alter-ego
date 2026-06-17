# WebSocket Debug: Cloudflare HTTP/2 + Double-Accept

> Status: Superseded — historical record (resolved; WS replaced by SSE per docs/plan-sse-migration-v2.md)

## Symptoms

- Publish page `GET /create/{id}/publish` returns `500` in browser (CF cache)
- `WebSocket connection to 'wss://marinssolutions.com/ws/chat/{id}'` fails in browser
- Works locally (curl to localhost:8000/443), fails through Cloudflare

## Root Causes Found

### 1. Backend double-accept (`chat.py`)

The Docker container's `chat.py` had `await websocket.accept()` in `connect()`, but `app.py` already calls `accept(subprotocol=token)` **before** calling `connect()`. This crashed the ASGI state machine:

```
RuntimeError: Expected ASMI message "websocket.send" or "websocket.close",
but got 'websocket.accept'
```

**Fix**: Removed `await websocket.accept()` from `chat.py:44` via `docker exec` + `sed`, then restarted the backend container.

### 2. Cloudflare HTTP/2 WebSocket (RFC 8441) not supported

Browsers default to HTTP/2. When creating a WebSocket over HTTP/2, they send an **extended CONNECT** frame with `:protocol: websocket` (RFC 8441). Cloudflare must convert this to HTTP/1.1 `Upgrade` for the origin.

**Test results**:
| Protocol | Test | Result |
|----------|------|--------|
| HTTP/1.1 | `curl --http1.1` through CF | `101` ✅ |
| HTTP/2 | `node.js http2 CONNECT` through CF | `400` ❌ |
| Direct (no CF) | `curl` to localhost | `101` ✅ |

Cloudflare returns `400` for the HTTP/2 extended CONNECT. The backend is never reached.

### 3. Frontend cookie/subprotocol mismatch

The frontend reads tokens from `document.cookie` (`frontend/src/features/chat/hooks/use-websocket-chat.ts:51`), but both `access_token` and `anon_token` are `httponly=True`. JavaScript cannot read them. The subprotocol is never sent. Backend **does** fall back to `websocket.cookies` — this path works when the request reaches the backend.

### 4. Cloudflare stale cache (publish page 500)

Local nginx returns `200` for the publish page. The `500` browser sees is Cloudflare serving a cached error from an earlier SSR failure. The `Cache-Control` headers (added previously) should prevent this going forward, but existing cached entries need purging.

## What Was Done

1. Fixed double-accept in running container
2. Verified WS works through all three paths with valid UUID + anon_token:
   - `localhost:8000` (backend direct) → 101
   - `localhost:443` (via nginx) → 101
   - `marinssolutions.com` (via Cloudflare + nginx, HTTP/1.1) → 101
3. Confirmed HTTP/2 WebSocket via Cloudflare returns 400
4. Tested that `test123` as conv_id caused `UUID()` ValueError (false lead in earlier session)

## Remaining Fixes Needed

### Quick fix (recommended)
- **Cloudflare Dashboard → Network**: Disable **HTTP/2** entirely. Browser falls back to HTTP/1.1, WebSocket `Upgrade` works.
- **Cloudflare Dashboard → Caching**: Purge **everything** (or the publish page path).

### Alternative fix
- **Enable HTTP/2 to Origin** in Cloudflare AND add `http2` to nginx's `listen 443 ssl` directive. Let Cloudflare forward the extended CONNECT directly.

### Long-term
- Fix the frontend subprotocol flow (read token from API response, not from httponly cookie)
- Revert debug logging from `app.py`
- Ensure `chat.py` in the Docker build doesn't contain the extra `accept()`

## Files Changed
- `backend/src/rag_backend/api/websocket/chat.py` (container only: removed `await websocket.accept()`)
- No repo changes needed (repo's `chat.py` already correct)
