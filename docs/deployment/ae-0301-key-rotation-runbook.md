# AE-0301 — Secret file permissions invariant + cheap-key rotation runbook

Status: active runbook (AE-0301). Expensive-secret rotation is **AE-0306** —
do not rotate `POSTGRES_PASSWORD`, `SECRET_KEY`, `ANON_SECRET_KEY`,
`LANGFUSE_ENCRYPTION_KEY`, or `LANGFUSE_SALT` from this document.

## The 600 invariant

Production secret files must be mode `600`, owned by root, with **no plaintext
`.env.backup.*` copies** in `/opt/alter-ego`:

- `/opt/alter-ego/.env` — rewritten from GitHub Secrets on **every** deploy
  (`.github/workflows/deploy.yml`). The deploy sets `umask 077` before the
  write (file is 600 from the first byte — no world-readable window) plus a
  defensive `chmod 600`.
- `/opt/alter-ego/backend/.env` — server-local (git-ignored, not rewritten by
  deploys); chmod'd defensively on each deploy.

Enforcement is `scripts/deploy/check-env-permissions.sh`, invoked at the end
of every deploy: a wrong mode/owner, a missing file, or a reappearing
`.env.backup.*` **fails the deploy** (stat-based assertion under `set -e`).
Rule-fires test: `backend/tests/unit/scripts_ci/test_check_env_permissions.py`.

History: the files were 644 (world-readable) for **at least 2026-05-04 (first
deploy) → 2026-07-01 (remediation), ~58 days — possibly since droplet creation
on 2026-04-28**. File mtimes are meaningless for this bound because each deploy
rewrites `.env`. The `.env.backup.20260602-211752` was a one-time manual `cp`
(no cron, deploy step, or repo script creates such backups); the deploy check
above turns "must not recur" into an enforced invariant.

## Per-provider exerciser list (hard gate — AE-0301 AC)

Facts verified on the droplet 2026-07-01: `LLM_PROVIDER=glm`;
`GEMINI_API_KEY` is empty **by design** (prod routes images to OpenAI — see
memory `prod-no-gemini-key-by-design`). DI wiring
(`backend/src/rag_backend/infrastructure/container.py`): RAG chat uses
`AnthropicLLMService` + `OpenAIEmbeddingService` + `PineconeVectorStore`;
the carousel LLM path uses the `LLM_PROVIDER` toggle
(`infrastructure/external/chat_model_factory.py`).

| Secret                                        | Active in prod?                         | Named exerciser                                          | "New key live and in use" assertion                                                                                                                                                                   |
| --------------------------------------------- | --------------------------------------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OPENAI_API_KEY`                              | Yes — carousel images + embeddings      | Prod carousel smoke (images phase)                       | Images phase completes; generated slide images render in the run                                                                                                                                      |
| `ANTHROPIC_API_KEY`                           | Yes — RAG chat `llm_service`            | Authenticated RAG chat request against prod              | Streamed completion succeeds; Langfuse trace shows an Anthropic generation post-rotation                                                                                                              |
| `GLM_API_KEY`                                 | Yes — system model (`LLM_PROVIDER=glm`) | Prod carousel smoke (content/orchestration phases)       | Content phase completes; Langfuse trace shows `glm-5.2` generations post-rotation                                                                                                                     |
| `PINECONE_API_KEY`                            | Yes — RAG retrieval `vector_store`      | The same authenticated RAG chat request (retrieval step) | Response carries retrieved context (non-empty sources); no Pinecone auth errors in backend logs                                                                                                       |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Yes — tracing                           | Either smoke above                                       | A **new** trace (post-rotation timestamp) is visible in the Langfuse UI                                                                                                                               |
| `GEMINI_API_KEY`                              | **No — excluded**                       | n/a                                                      | Nothing to rotate or revoke: key is empty in prod by design                                                                                                                                           |
| `LANGFUSE_MINIO_PASSWORD`                     | Yes — MinIO root + Langfuse S3 upload   | Langfuse event upload (any traced smoke)                 | New traces' event blobs land in MinIO post-rotation; no S3 auth errors in langfuse/worker logs. Added by AE-0304: the real value sat in plaintext in `compose.langfuse-s3-test.yml` in the deploy dir |

Pre-decisions (recorded here, not made at execution time):

- **GLM**: exercised — confirmed, not assumed: `LLM_PROVIDER=glm` read from the
  live prod `.env`, and the chat-model factory routes the carousel/content LLM
  to GLM whenever that toggle is set with a non-empty key.
- **Pinecone**: named exerciser is the prod RAG chat request's retrieval step
  (option (i)-equivalent — an existing path, no new exerciser needed). Not
  revoke-on-faith.
- **Anthropic**: exercised by RAG chat, **not** by the carousel smoke (the
  carousel LLM is GLM in prod) — a carousel-only smoke must not green-light
  revoking the Anthropic key.
- **Gemini**: excluded (inactive by design).

## Rotation procedure (cheap keys — revoke-after-verify, per provider)

For **each** provider independently — never as one bundled smoke:

1. Generate a new key in the provider dashboard (old key stays valid).
2. Update the matching GitHub Secret (`gh secret set <NAME>`).
3. Redeploy (merge/dispatch `deploy.yml`) — the deploy rewrites
   `/opt/alter-ego/.env` from Secrets.
4. Run **that provider's named exerciser** (table above) and confirm its
   "live and in use" assertion.
5. Only then revoke the old key in the provider dashboard.
6. Re-run the exerciser once more after revocation (proves traffic is on the
   new key, not the just-revoked one).

Coordination: deploys are serialized (`concurrency: prod-deploy`), and the
AE-0303 auto-reboot lock must not fire mid-rotation — hold rotation while a
maintenance reboot window is open.

## One-time remediation (droplet) — executed 2026-07-01

```bash
mkdir -p /root/env-backups && chmod 700 /root/env-backups
mv /opt/alter-ego/.env.backup.20260602-211752 /root/env-backups/  # relocated, 600
chmod 600 /root/env-backups/.env.backup.20260602-211752
chmod 600 /opt/alter-ego/.env /opt/alter-ego/backend/.env
sed -i 's/^DEBUG=true$/DEBUG=false/' /opt/alter-ego/backend/.env
stat -c '%a %U %n' /opt/alter-ego/.env /opt/alter-ego/backend/.env  # → 600 root
```

`docker-compose.prod.yml` hardcodes `DEBUG: "false"` for the backend; the
at-rest edit only removes the footgun value.
