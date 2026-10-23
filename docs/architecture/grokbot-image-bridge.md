# GrokBot Image Bridge (AE-0393)

> Status: proposed — see [ADR-0022](../decisions/0022-grokbot-image-bridge.md).
> Goal: generate carousel slide images through the owner's Grok Bot (Cursor subscription)
> instead of the paid OpenAI Images API, **without changing the carousel workflow**.

## 1. Summary

The images phase already talks to images through one port,
`ImageGenerationService.generate_image(prompt, output_path) -> str`, resolved per
`(model, style)` by `ImageProviderRegistry`. The bridge is a new implementation of that port,
`GrokBotImageService`. It is wired in **in place of** `OpenAIImageService` when the flag is on, and
wrapped in a fallback that calls the real OpenAI service on any bridge failure.

The Grok Bot is asynchronous: it is triggered by a webhook and needs ~45–90 s per image. So the
bridge is an **async job with a callback**:

```
images node ──generate_image(prompt, path)──▶ FallbackImageService
                                                │ primary
                                                ▼
                                       GrokBotImageService
   1. INSERT image_bridge_jobs (pending, token hash, expires_at)
   2. POST  GROKBOT_IMAGE_WEBHOOK_URL  {job_id, prompt, size, callback_url, callback_token}
   3. poll the job row every 2 s until succeeded | failed | expired
                                                ▲
        Grok Bot (Cursor routine) generates the image, then
   4. POST /api/v1/image-bridge/jobs/{job_id}/result   (OpenAI ImagesResponse body)
      → validate, decode, store bytes, mark succeeded
   5. waiter writes the bytes to output_path (normalized to the requested size) and returns
                                                │ any failure / timeout
                                                ▼
                                       OpenAIImageService (unchanged)
```

Nothing upstream of the port changes: prompts, style strategies, the per-minute cap, the
artifact checks and the autopilot gates all stay as they are.

## 2. Webhook contract (what the Grok Bot side implements)

### 2.1 Outbound — alter-ego → Grok Bot

`POST {GROKBOT_IMAGE_WEBHOOK_URL}`

Headers: `Content-Type: application/json`, plus one auth header whose **name and value are
configuration** (`GROKBOT_IMAGE_WEBHOOK_AUTH_HEADER`, default `Authorization`;
`GROKBOT_IMAGE_WEBHOOK_AUTH_VALUE`, e.g. `Bearer …`), so it matches whatever the Cursor webhook
expects.

```json
{
  "job_id": "6f1c2a9e-4c1b-4f7e-9a51-2d8f0c7b3e10",
  "model": "gpt-image-2",
  "prompt": "<full rendered image prompt, style strategy already applied>",
  "size": "1536x1024",
  "n": 1,
  "response_format": "b64_json",
  "callback_url": "https://<public-host>/api/v1/image-bridge/jobs/6f1c2a9e-…/result",
  "callback_token": "<one-time random token, 43 chars url-safe>",
  "expires_at": "2026-10-15T20:10:00Z",
  "metadata": { "project_id": "…", "content_type": "carousel" }
}
```

Expected reply: any `2xx` within 15 s (accepted). A non-2xx or a timeout fails the job
immediately; no waiting, so the fallback runs at once.

### 2.2 Callback — Grok Bot → alter-ego

`POST /api/v1/image-bridge/jobs/{job_id}/result`

Headers: `Content-Type: application/json`, `X-Image-Bridge-Token: <callback_token>`.

**Success body: the OpenAI Images API response shape** (`ImagesResponse`):

```json
{
  "created": 1760558400,
  "data": [
    { "b64_json": "<base64 PNG/JPEG/WEBP>", "revised_prompt": "optional" }
  ]
}
```

**Failure body: the OpenAI error shape**, e.g. a refusal or a generation error:

```json
{ "error": { "type": "image_generation_error", "code": "content_policy", "message": "…" } }
```

Rules:

- Only `data[0].b64_json` is read. `url` responses are **not** supported, which avoids SSRF and
  outbound fetches.
- Max request body 16 MB (nginx location limit; the decoded image must be ≤ 12 MB).
- The image must decode with Pillow as PNG, JPEG or WEBP, with each side 512–4096 px.

| Status | Meaning |
|---|---|
| `202` | Accepted (success or error recorded). |
| `401` | Missing/invalid `X-Image-Bridge-Token`. Same response for an unknown `job_id`, so job ids cannot be probed. |
| `409` | Job is no longer pending (already completed, failed or expired). Idempotent: a repeat of the *same* success returns `409`, not a second write. |
| `413` | Body too large. |
| `422` | Body is neither a valid ImagesResponse nor an error, or the image fails validation. The job is marked failed. |

## 2.3 Experiment (2026-10-15)

The owner ran the contract by hand through the Grok Bot, posting to a webhook.site inbox
instead of our callback:

- **Result:** the image arrived exactly 1536×1024 as a PNG of 2,135,995 bytes. The callback body
  was 2,848,043 bytes and arrived intact, with `X-Image-Bridge-Token` present, and the POST
  returned HTTP 200.
- **How it was made:** the Grok Bot generated the image through the Codex CLI (0.162.1) and its
  built-in image tool, on the owner's ChatGPT account.
- **Timing:** 63 s for the Codex run and ≈75 s for the whole job.
- **Grok Bot-side requirements for unattended runs:**
  - run `codex exec` non-interactively with stdin closed (`< /dev/null`) and a hard timeout. The
    first attempt hung for 10 minutes waiting for keyboard input.
  - grant a standing approval for the upload to the callback host.
- **Still to verify:** routine runs are queued, so parallelism and start latency are not
  guaranteed. The bridge timeout (600 s) and the fallback cover this.

## 2.4 Image-edit jobs: a cover from the owner's photos (AE-0508)

Same endpoint, same auth header, same callback. A slide-1 cover generated from the owner's
library photos (publish step, "Gerar capa com Grok") adds two keys to the §2.1 body; a
text-only job never sends them.

```json
{
  "job_id": "…",
  "model": "gpt-image-2",
  "prompt": "<cover instruction with the owner's direction inside>",
  "size": "1080x1350",
  "task": "image_edit",
  "reference_images": [
    { "b64_json": "<base64 PNG>", "mime_type": "image/png" }
  ],
  "metadata": { "project_id": "…", "content_type": "carousel_cover" },
  "…": "the other §2.1 fields"
}
```

- `reference_images`: 1–3 of the owner's library photos, chosen per generation. Re-encoded by
  the backend as PNG, at most 1024 px a side, every metadata block (EXIF, GPS, XMP) dropped.
  Bytes only: no URL to the photo ever leaves the app. A body is about 1–5 MB (up to three
  photos of about 1–1.5 MB each, base64-encoded).
- The Grok Bot runs image-to-image with those photos as the reference (the person must stay
  recognisable) and answers through the §2.2 callback exactly as for a text job.
- The backend fits the answer to 1080×1350, applies the `ai_image` cover rules (ADR-0024) and
  stores it as a private creator asset with role `cover`. No OpenAI fallback for these jobs.
- Each generation follows an explicit confirmation by the owner, at most 4 per carousel and 40
  per calendar month (failures do not count); see [ADR-0027](../decisions/0027-grok-cover-from-library-photos.md).

## 3. Backend design

### 3.1 Module

New bounded context `modules/image_bridge/`, following the `modules/autopilot` layout
(`domain/`, `application/`, `infrastructure/`, `api/`, `public.py`, `constants.py`). Only
`public.py` is imported from outside the module.

- `domain/models.py`
  - `ImageBridgeJob`: id, status, size, token_sha256, created_at, expires_at, completed_at,
    error_code, error_message.
  - `ImageBridgeJobStatus`: `pending | succeeded | failed | expired`.
- `domain/ports.py`: the job repository, the webhook client and a clock.
- `application/grokbot_image_service.py`: `GrokBotImageService(ImageGenerationService)`.
  - Uses a semaphore, `IMAGE_BRIDGE_MAX_CONCURRENCY`, default 2.
  - Steps: create the job, POST the webhook, wait, then write the output.
  - Raises `RuntimeError` on failure/expiry, the same contract as `OpenAIImageService`.
- `application/fallback_image_service.py`: `FallbackImageService(primary, fallback)`.
  - Logs and traces which provider produced the image.
  - Calls the fallback on any primary exception when `IMAGE_BRIDGE_FALLBACK_ENABLED`.
- `application/callback.py`: validates and records a callback (pure parsing in `domain/`).
- `infrastructure/`: SQLAlchemy repository (`image_bridge_jobs` table), `httpx` webhook client,
  Pillow decode + normalize.
- `api/routes.py`: the callback route above. Auth is a constant-time compare of
  `sha256(token)` against `token_sha256` (`hmac.compare_digest`), the same pattern as
  `autopilot/api/auth.py`.

### 3.2 Waiting across workers

The callback can land on any uvicorn worker, so the waiter **polls Postgres** (every 2 s, `SELECT`
by primary key), not an in-process event. Image bytes go in `image_bridge_jobs.image_bytes`
(`bytea`), written by the callback, read once by the waiter, then nulled. That needs no shared
filesystem.

Timeout: `IMAGE_BRIDGE_TIMEOUT_SECONDS` (default 600; Grok Bot runs are queued, so start time is not guaranteed). `expires_at = created_at + timeout`.
On timeout the waiter marks the job `expired`, and late callbacks get `409`.

### 3.3 Output normalization

The waiter writes the image to `output_path` at **exactly the size that was requested**
(`IMAGE_SIZE` of the OpenAI service, today `1536x1024`). It uses Pillow `ImageOps.fit` with
LANCZOS and keeps the format the OpenAI path produced (PNG). The rest of the pipeline therefore
sees the same artifact it gets from OpenAI today.

### 3.4 Wiring and flags

`container.py`: when `IMAGE_BRIDGE_ENABLED=true`, `openai_service` passed to
`ImageProviderRegistry` becomes `FallbackImageService(primary=GrokBotImageService(...),
fallback=OpenAIImageService(...))`. When false (the code default), nothing changes.

**Owner decision (2026-10-15): the bridge is ON in prod.** `deploy.yml` sets
`IMAGE_BRIDGE_ENABLED=true` and `IMAGE_BRIDGE_FALLBACK_ENABLED=true`: the Grok Bot replaces the
OpenAI Images API as the normal path, and OpenAI runs only when a bridge job fails. The
`Settings` defaults stay `false` / `true`, so dev and tests never call a webhook.

| Setting | Default (code) | Prod (`deploy.yml`) | Notes |
|---|---|---|---|
| `IMAGE_BRIDGE_ENABLED` | `false` | `true` | Master switch. |
| `IMAGE_BRIDGE_FALLBACK_ENABLED` | `true` | `true` | On failure, call OpenAI. |
| `IMAGE_BRIDGE_TIMEOUT_SECONDS` | `600` | `vars` or `600` | Per image; includes the Grok Bot queue wait. |
| `IMAGE_BRIDGE_MAX_CONCURRENCY` | `2` | `vars` or `2` | Bridge jobs in flight per process. |
| `IMAGE_BRIDGE_PUBLIC_BASE_URL` | — | `https://marinssolutions.com` | Builds `callback_url`; needed when enabled. |
| `GROKBOT_IMAGE_WEBHOOK_URL` | — | secret | Needed when enabled. |
| `GROKBOT_IMAGE_WEBHOOK_AUTH_HEADER` | `Authorization` | `vars` or `Authorization` | |
| `GROKBOT_IMAGE_WEBHOOK_AUTH_VALUE` | — | secret | |

Startup check: prod auto-deploys on merge, so a missing secret must never crash-loop the
backend. When the bridge is enabled but `GROKBOT_IMAGE_WEBHOOK_URL` or
`IMAGE_BRIDGE_PUBLIC_BASE_URL` is empty, startup logs **one ERROR**
(`image_bridge_misconfigured`, `missing=[names]`, never values) and the container wires the plain
`OpenAIImageService`. Startup never fails because of the bridge.

All of these must be added to `.github/workflows/deploy.yml` (the deploy rewrites the server
`.env` from GitHub Secrets) and to `.env.example`. The `backend:autopilot-env` gate pattern
shows how settings are checked against `deploy.yml`.

As implemented (AE-0393):

- `deploy.yml` reads `GROKBOT_IMAGE_WEBHOOK_URL` and `GROKBOT_IMAGE_WEBHOOK_AUTH_VALUE` from
  **secrets**. The flag, the fallback and the public base URL are literals (the switch and
  the rollback are reviewed code); timeout, concurrency and the auth header name are
  repository variables (`vars.*`) with the defaults above.
- `docker-compose.prod.yml` passes all eight to the backend service (`IMAGE_BRIDGE_ENABLED`
  defaults to `false`).
- `scripts/ci/check_image_bridge_env_parity.py` runs inside `backend:autopilot-env`. It checks
  that every setting is on all four surfaces (deploy, compose, `backend/.env.example`,
  `Settings`), that the two secrets are secrets and the others are not, that compose and
  `.env.example` default the flag to false, and that `deploy.yml` keeps the owner decision
  (literal flag, fallback `true`, the site origin).
- `run_startup_validations` calls `report_image_bridge_config`, which logs the
  `image_bridge_misconfigured` ERROR described above; the container's builder then keeps OpenAI.
- The sweep (expire overdue `pending` rows, delete rows older than 7 days) runs lazily before
  each new job; a callback on an overdue job also expires it and answers `409`.
- Smoke test: `scripts/image_bridge_smoke.py` (bridge only by default; `--with-fallback`
  allows OpenAI). On prod, pipe it into the backend container:
  `docker compose -f docker-compose.prod.yml exec -T backend python - < scripts/image_bridge_smoke.py`.

### 3.5 Schema

New table `image_bridge_jobs`, with an Alembic migration. Prod creates missing tables at startup,
so no hand-applied SQL is needed for a brand-new table. Columns: `id uuid pk`, `status`, `size`,
`token_sha256`, `image_bytes bytea null`, `error_code`, `error_message`, `created_at`,
`expires_at`, `completed_at`. Index on `(status, expires_at)`. A sweep (on the existing autopilot
tick, or lazily on read) expires stale `pending` rows. Succeeded rows have `image_bytes` nulled
after the read, and rows older than 7 days are deleted.

### 3.6 nginx

Add a location for `/api/v1/image-bridge/` with `client_max_body_size 16m` in both `nginx.conf`
and `nginx.conf.ssl`. The global default (1 MB) would reject every callback with `413`.

### 3.7 Observability

- Langfuse/structlog fields per image: `image_provider = grokbot | openai_fallback | openai`,
  `bridge_job_id`, wait seconds, failure reason.
- No secrets, tokens or base64 in logs.

## 4. Failure modes

| Case | Result |
|---|---|
| Webhook non-2xx / timeout | Job `failed` at once → OpenAI fallback. |
| Grok Bot never calls back | Job `expired` after the timeout → fallback. |
| Grok Bot returns an OpenAI error body (refusal) | Job `failed` with code/message → fallback (configurable). |
| Invalid/oversized image | `422`, job `failed` → fallback. |
| Duplicate / late callback | `409`; no state change. |
| Fallback disabled + any failure | `RuntimeError`, the same as an OpenAI failure today (existing retry/escalation path). |

## 5. Security

- The per-job one-time token is stored only as SHA-256 and compared in constant time. It is
  scoped to one job and expires with it. The callback needs no global key.
- A `401` for an unknown job or a bad token alike, so job ids cannot be enumerated.
- `b64_json` only; no URL fetching (no SSRF). Pillow decode with size and pixel limits
  (`Image.MAX_IMAGE_PIXELS`), plus the body-size cap.
- The webhook URL and auth value are secrets (pydantic `SecretStr`), never logged.

## 6. Rollout

The merge **is** the enable: `deploy.yml` ships `IMAGE_BRIDGE_ENABLED=true` and every merge to
`main` auto-deploys.

1. **Before the merge:** set the `GROKBOT_IMAGE_WEBHOOK_URL` and
   `GROKBOT_IMAGE_WEBHOOK_AUTH_VALUE` secrets, and make sure the Grok Bot routine is live
   against the contract (section 2). Without the secrets the deploy still comes up: it logs
   `image_bridge_misconfigured` and keeps plain OpenAI.
2. Merge → deploy. Check the startup log has no `image_bridge_misconfigured`.
3. **Post-deploy check:** run `scripts/image_bridge_smoke.py` against prod. It runs one bridge
   job end to end and prints seconds, dimensions and provider (exit 0 = image written).
4. Watch one autopilot carousel: `image_provider` per image (`grokbot` vs `openai_fallback`),
   fallback count, wait times.
5. **Rollback:** set `IMAGE_BRIDGE_ENABLED=false` in `deploy.yml` and merge (plain OpenAI).
6. Keep OpenAI as the fallback. Revisit after two weeks of fallback rate data.
