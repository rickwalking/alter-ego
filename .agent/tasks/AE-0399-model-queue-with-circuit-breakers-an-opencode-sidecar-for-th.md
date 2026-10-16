# AE-0399 — Model queue with circuit breakers, an OpenCode sidecar for the free model, and breaker alerts

Status: In Development
Tier: T1
Priority: P0
Type: Bug
Area: backend
Owner: Claude (owner-requested hotfix)
Agent Lane: developer → qa → release
Branch: fix/ae-0399-model-queue-breaker
Kanban Card: TBD
Created: 2026-10-16
Updated: 2026-10-16

## Goal

Each carousel LLM role runs on an ordered queue of models (fast: free DeepSeek V4.1 Flash, then DeepSeek V4.1 Flash, then Qwen). A per-model circuit breaker and debounce decide, from the model's response, whether to retry, wait, or skip the model. Breaker changes reach the owner on a separate Telegram alerts bot.

## Problem

Prod 2026-10-16: the OpenCode Go weekly quota ran out mid-run (429 usage limit). The AE-0395 policy retried the exhausted model 5 times with backoff on every call before falling back, so each call paid for minutes of useless retries. There was no memory across calls, and no alert. The owner also wants the free DeepSeek model first. It only answers from inside OpenCode (a direct API call gets 403 `FreeTierError`), and the free tier refuses any restricted permission config.

## Scope

- `infrastructure/llm/model_breaker.py`: failure classes (fatal, quota, throttled, transient, content), a per-model CLOSED/OPEN/HALF_OPEN breaker with a single half-open probe and a doubling cooldown, and a process-wide registry that publishes transitions.
- `infrastructure/external/model_queue_chat_model.py`: a `BaseChatModel` that walks the queue.
  - Fatal and quota failures give up on the model at once.
  - Transient failures retry with backoff and jitter.
  - A 429 rate limit is debounced (Retry-After or 1-4 s).
  - Empty answers are re-rolled.
  - Bad JSON moves on to the rest of the queue (`as_fallback`).
  - When every model fails, `AllModelsUnavailableError` names each model's state.
- `infrastructure/external/opencode_sidecar_model.py`: a client for `opencode serve` (Basic auth, one session per call).
- `ops/opencode/Dockerfile` and the compose service `opencode`:
  - isolated: no secrets, no ports, a read-only root, tmpfs, `cap_drop: ALL`;
  - the login is kept in the `opencode_data` volume.
- `infrastructure/external/model_queue_factory.py` builds the queue from `LLM_MODEL_QUEUE_FAST` / `_REASONING`. When neither is set, the AE-0391 routing is kept.
- `infrastructure/notifications/llm_alerts.py`: a send-only Telegram bot.
  - One message per open or close; half-open is skipped.
  - "All models down" is sent at most once per 15 min.
- Settings, `deploy.yml`, `docker-compose.prod.yml`, `.env.example` and the autopilot env-parity gate.

## Non-Goals

- Persisting breaker state across restarts (the state is per process and rebuilt from live failures).
- Changing prompts or model ids of the AE-0391 routing.
- Tools or permissions inside the sidecar (the free tier refuses restricted configs; isolation is the container).

## Acceptance Criteria

- [x] AC1: The first model with a closed breaker answers; the later models are not called.
- [x] AC2: 401/403/FreeTierError opens the breaker for 6 h after one call, and the next call skips the model.
- [x] AC3: A 429 usage limit opens it for 1 h without retries.
- [x] AC4: Transient errors are tried 3 times with backoff, then the breaker opens.
- [x] AC5: A 429 rate limit waits Retry-After (capped) and retries the same model.
- [x] AC6: An empty answer is re-rolled 3 times, then the call moves on; the breaker stays closed.
- [x] AC7: Only one probe passes a half-open breaker; a failed probe doubles the cooldown (max 1 h).
- [x] AC8: When all models are down, the error names each state and the all-down alert fires.
- [x] AC9: The sidecar call uses Basic auth, one session per call, the model and the system prompt. A model error keeps its provider status.
- [x] AC10: Alerts: one per open, none for half-open, all-down rate-limited; no token means alerts are off.
- [x] AC11: Without a queue setting the routed model is kept. A sidecar entry without a URL is dropped.
- [x] AC12: JSON that never parses moves on to the rest of the queue.

## Gherkin Scenarios

`backend/tests/features/llm_model_queue_ae0399.feature`.

## Delta

### ADDED

- `backend/src/rag_backend/infrastructure/config/llm_queue_constants.py`
- `backend/src/rag_backend/infrastructure/llm/model_breaker.py`
- `backend/src/rag_backend/infrastructure/external/model_queue_chat_model.py`
- `backend/src/rag_backend/infrastructure/external/model_queue_factory.py`
- `backend/src/rag_backend/infrastructure/external/opencode_sidecar_model.py`
- `backend/src/rag_backend/infrastructure/notifications/` (`llm_alerts.py`)
- `ops/opencode/Dockerfile`
- `backend/tests/features/llm_model_queue_ae0399.feature`
- `backend/tests/unit/infrastructure/test_model_queue_ae0399.py`

### MODIFIED

- `backend/src/rag_backend/infrastructure/config/settings.py`
- `backend/src/rag_backend/infrastructure/external/chat_model_factory.py`
- `backend/src/rag_backend/infrastructure/external/routed_chat_model.py` (`HasFallback`)
- `.github/workflows/deploy.yml`, `docker-compose.prod.yml`, `backend/.env.example`
- `scripts/ci/check_autopilot_env_parity.py` and its test
- `docs/backend/llm-model-routing.md`, `backend/CLAUDE.md`

### REMOVED

- None.

## Affected Areas

- Backend: LLM model construction for every carousel role
- Frontend: none
- Database: none
- API: none
- Tests: unit + feature
- Docs: llm-model-routing.md
- Prompts/LLM: model selection only
- Observability: breaker logs + Telegram alerts
- Deployment: new `opencode` service + volume, 3 new secrets (`OPENCODE_SERVER_PASSWORD`, `TELEGRAM_ALERTS_BOT_TOKEN`, `TELEGRAM_ALERTS_CHAT_ID`)

## Dependencies

- Blocks: autopilot runs surviving quota exhaustion
- Blocked by: none
- Related: AE-0391, AE-0395

## Implementation Plan

1. Breaker + classification.
2. Queue model + factory hook.
3. Sidecar client + container.
4. Alerts bot.
5. Tests, docs, deploy wiring.

## QA Checklist

- [x] Security reviewed: the sidecar has no secrets and no ports. The backend never shares its env with it, and its password is used only on the compose network.
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-16

Plan agreed with the owner ("Yes, as a hotfix", "do it with the sidecar"). Implemented and tested.

## Files Touched

See Delta.

## Test Evidence

- `test_model_queue_ae0399.py`: 25 passed; routing/JSON-retry suites green.

## QA Report

Pending (hotfix fast path: CI Test & Coverage decides).

## Decision Log

- 2026-10-16: The free model runs in a sidecar. OpenCode is an agent with shell tools, and the free tier refuses restricted permissions, so isolation is the container itself.
- 2026-10-16: Breaker state is per process. Rebuilding it from a few live failures is cheap, and persisting it is not worth a table for a hotfix.

## Blockers

None. Post-deploy owner steps:
- run `opencode auth login` in the sidecar;
- create the alerts bot;
- set the 3 secrets.

## Final Summary

Pending.
