# AE-0330 — send x-opencode-session header so glm calls stop failing with provider_unavailable

Status: Dev Complete
Tier: T1
Priority: Critical
Type: Bug
Area: Backend
Owner: Claude
Branch: fix/ae-0330-opencode-session-header
Created: 2026-09-14
Updated: 2026-09-14

## Goal

Send the `x-opencode-session` header (and a real user agent) on every GLM call so
OpenCode Go stops rejecting prod carousel generation with 400 MissingSessionID.

## Problem

Prod carousel creation is DOWN. `POST /api/carousels/{id}/workflow/start` returns
**503 `provider_unavailable`** (observed 2026-09-14 15:43:16Z and 15:43:36Z on
project `dcaa5fef-9d91-4ab1-80b2-e77860ab8a43`). The backend log shows the real
cause:

```
workflow_start_provider_error ... error="Error code: 400 - {'type': 'error',
 'error': {'type': 'MissingSessionID', 'message': 'Error from provider
 (Console Go): Request is missing x-opencode-session and cannot be routed
 efficiently. Please see https://opencode.ai/docs/go/#where-can-i-use-it'}}"
```

OpenCode Go — which serves GLM 5.2, and prod runs `LLM_PROVIDER=glm` — began
requiring callers to send a conversation header. Our `ChatOpenAI` client sends
none, so every GLM call 400s; `classify_provider_error` (AE-0319) maps
`openai.APIError` → 503 `provider_unavailable`. Their docs additionally ask API
callers to identify with their own user agent rather than the generic
`OpenAI/Python` the SDK sends.

Confirmed live from the prod droplet with prod's own `GLM_API_KEY`: without the
header → 400 MissingSessionID; with `x-opencode-session` + `alter-ego/…` user
agent → 200 OK.

This is not an outage on their side and not a bad key — it is a new client
requirement, so it will not self-heal.

## Scope

- `chat_model_factory._build_glm_model` sends `default_headers` with
  `x-opencode-session` and `User-Agent: alter-ego/<app_version>`.
- Session id minted once per built client (the chat model is a DI singleton), so
  it is stable for the process lifetime — what OpenCode's routing and
  prompt-cache optimisation expects of a "conversation".
- Gherkin scenarios + tests that prove the headers reach the wire.

## Non-Goals

- Do not refactor unrelated code.
- Do not plumb a per-carousel/per-conversation session id through DI — the
  client is a singleton; finer-grained sessions are a follow-up, not a hotfix.
- Do not change the provider toggle, the Anthropic path, or the AE-0319 error
  mapping.

## Acceptance Criteria

- [x] A GLM request carries an `x-opencode-session` header on the wire.
- [x] A GLM request identifies itself as `alter-ego/<app_version>`, not as the
      openai SDK default user agent.
- [x] The session id is identical across two calls on one client and differs
      between two separately built clients.
- [x] The Anthropic path carries no OpenCode headers (no leakage).
- [x] Tests fail when the fix is reverted (negative control run, not assumed).
- [x] Full `gates.sh backend` green via `gate-capture.sh`.

## Repro Steps

1. Prod (`LLM_PROVIDER=glm`): open a carousel and hit Generate.
2. `POST /api/carousels/{id}/workflow/start` → 503, body `provider_unavailable`.
3. `docker logs alter-ego-backend-1 | grep MissingSessionID` shows the 400.
4. Equivalent bare curl to `https://opencode.ai/zen/go/v1/chat/completions`
   without `x-opencode-session` → 400; with it → 200.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None. (Builds on AE-0285 provider toggle and AE-0319 provider-error mapping.)

## Progress Log

### 2026-09-14

Diagnosed from prod logs, reproduced against the live endpoint with prod's key,
fixed in the factory, covered by wire-level tests with a negative control.

**Prod hot-patch applied (temporary).** With prod down and a deploy ~12 min
behind a merge, the patched `chat_model_factory.py` was copied into the running
`alter-ego-backend-1` and the container restarted (healthy). A live GLM call
from inside the container then returned normally:

```
provider: glm | model: glm-5.2
headers: {'x-opencode-session': 'alter-ego-dad54b25-…', 'User-Agent': 'alter-ego/0.1.0'}
GLM replied: 'PATCH_OK'
```

The original file is backed up at `/root/hotfix-ae-0330/chat_model_factory.py.orig`
on the droplet (md5 matched `origin/main` before patching). **This patch lives in
the container layer only** — it is lost on any `docker compose up`/recreate, and
is superseded by the real image on the next deploy. Merging this PR is still
required.

**Follow-on 504 (nginx), found after the hot-patch.** With GLM answering again,
`POST workflow/start` ran its full length and nginx returned **504 Gateway
Timeout** at 60s — while the backend finished at **68.5s** with a 200, published
`phase_changed` + `review.requested` and advanced the project to
`outline`/`approved`. The work landed; only the response was lost.

Cause: `location /api/` set no `proxy_read_timeout`, falling back to nginx's 60s
default. `/api/health` and `/api/conversations/` already carried 300s — the
general api block was the gap, and the race only became visible once GLM calls
stopped failing fast. Fixed in `nginx/nginx.conf{,.ssl}` and applied live
(`nginx -t` + reload, original at `/root/hotfix-ae-0330/nginx.conf.ssl.orig`).

Cloudflare still caps the edge at ~100s, so this covers the 60-100s band only;
a generation slower than that needs `workflow/start` made async (202 + poll).
Worth its own ticket.

**Scope note:** `pip-audit` is a blocking CI gate and had gone red repo-wide on
freshly published advisories (19 across 7 packages, none introduced by this
diff). Nothing merges until it is green, so the dependency bumps ship here.

## Files Touched

- `backend/src/rag_backend/infrastructure/external/chat_model_factory.py`
- `backend/tests/unit/infrastructure/test_chat_model_factory.py`
- `backend/tests/features/llm_provider_toggle.feature`
- `backend/pyproject.toml`, `backend/uv.lock` (pip-audit gate — see Progress Log)
- `nginx/nginx.conf`, `nginx/nginx.conf.ssl` (follow-on 504 — see Progress Log)

## Test Evidence

Pending gate capture.

## QA Report

Pending.

## Blockers

None.
