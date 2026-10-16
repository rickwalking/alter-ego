# AE-0395 — LLM same-model retries, non-GLM fallbacks, and POV photo/art/palette variety

Status: In Development
Tier: T1
Priority: P0
Type: Bug
Area: backend
Owner: Claude (owner-requested hotfix)
Agent Lane: developer → qa → release
Branch: fix/ae-0395-llm-retry-pov-variety
Kanban Card: TBD
Created: 2026-10-16
Updated: 2026-10-16

## Goal

Make the autopilot pipeline run end to end without model failures, and make each new POV carousel look different: a new owner photo, neo-anime point-slide art, and a different palette.

## Problem

The first end-to-end POV run (project 64f13017, 2026-10-16) exposed:

1. **One bad model answer failed a whole phase.** The fast model returned prose instead of JSON for one call and the content phase failed. Each call got a single try before falling back.
2. **The GLM-5.3 fallback is unusable.** It returned empty content after ~8.5 minutes, four times in a row (35 minutes lost, then the phase failed).
3. **Every POV carousel reused the same photo.** `hook_photo_id` preferred the *most recently used* photo.
4. **Every POV carousel used the same flat art** (`pov_editorial` was forced).
5. **Every autopilot carousel had the same palette.** `auto` puts nearly every AI topic on `ai_competition` (blue/amber).
6. **The Grok Bot routine dropped one of two parallel image jobs.**

## Scope

- `RoutedChatModel`: `LLM_ATTEMPTS_PER_MODEL` (5) attempts per model for a timeout, an error (except 401/403) or empty content, with backoff 2/4/8/15/15 s, then the role's fallback with 5 attempts too.
- `ainvoke_json`: 5 attempts (each with its re-roll and repair) per model before the fallback.
- Fallbacks: fast role `qwen3.8-flash`, reasoning role `qwen3.8-max` (new `LLM_MODEL_FALLBACK_REASONING`); the fallback timeout drops 900 s → 180 s. Benchmarked on the prod endpoint (`docs/backend/llm-model-routing.md`).
- Photo rotation: a never-used hook photo first (newest first), then the least recently used.
- POV art: the scout's explicit supported style, else `neo_anime` (was always `pov_editorial`).
- Palette: the autopilot rotates 9 dark built-in themes per São Paulo day (`rotated_theme`), excluding `ai_competition`.
- `IMAGE_BRIDGE_MAX_CONCURRENCY` default 2 → 1.
- Scout routine v3 text: POV `image_style` now sets the point-slide art.

## Non-Goals

- Changing the primary models or the persona voice gate.
- Frontend.

## Acceptance Criteria

- [x] AC1: A transient failure is retried on the same model (up to 5 attempts) before the fallback is called.
- [x] AC2: The fallback also gets 5 attempts; auth errors are never retried.
- [x] AC3: Bad JSON gets 5 attempts on the same model before the fallback.
- [x] AC4: No role falls back to GLM (fast → qwen3.8-flash, reasoning → qwen3.8-max).
- [x] AC5: Consecutive POV carousels use different owner photos while the library has another one.
- [x] AC6: POV point slides default to neo-anime; an explicit supported scout style wins.
- [x] AC7: Consecutive São Paulo days get different dark palettes.
- [x] AC8: The bridge runs one Grok Bot job at a time in prod.

## Gherkin Scenarios

- `backend/tests/features/llm_retry_ae0395.feature` (new, 7 scenarios)
- `backend/tests/features/autopilot_variety_ae0395.feature` (new, 4 scenarios)
- `backend/tests/features/autopilot_pov_thesis.feature` (photo rotation ×2, the POV art outline)

## Delta

### ADDED

- `backend/tests/unit/infrastructure/test_llm_retry_ae0395.py`
- `backend/tests/unit/autopilot/test_pov_variety_ae0395.py`
- The two feature files above

### MODIFIED

- `infrastructure/external/routed_chat_model.py`, `chat_model_factory.py`, `config/llm_routing_constants.py`, `config/settings.py`
- `agents/llm_json_retry.py`
- `modules/editorial/infrastructure/pov_inputs.py` (rotation)
- `modules/autopilot/application/run_spec.py`, `pov_constants.py`, `domain/carousel_defaults.py`, `infrastructure/editorial_driver.py`
- `.github/workflows/deploy.yml`, `docker-compose.prod.yml`, `backend/.env.example`, `ops/grokbot/grok-bot/v3/routine.md`, docs
- Tests updated to the new contracts (AE-0391 routing/JSON, content/outline agents, parallel drafting, POV spec, photo ACL, driver theme)

### REMOVED

- GLM-5.3 as the default fallback.

## Affected Areas

- Backend: LLM routing, autopilot carousel spec
- Frontend: none
- Database: none (no schema change)
- API: none
- Tests: unit + integration + features
- Docs: llm-model-routing.md, backend CLAUDE.md, routine.md
- Prompts/LLM: fallback models
- Observability: `llm_retry` / `llm_json_retry` logs
- Deployment: new env `LLM_MODEL_FALLBACK_REASONING`; defaults changed in deploy.yml

## Dependencies

- Blocks: the 2026-10-17 autopilot run
- Blocked by: none
- Related: AE-0391, AE-0393, AE-0394

## Implementation Plan

1. Same-model retries in `RoutedChatModel` and `ainvoke_json`.
2. Per-role non-GLM fallbacks, benchmarked on the prod endpoint.
3. Photo rotation, the POV neo-anime default and the daily palette rotation.
4. Deploy defaults and docs; tests and feature scenarios.

## QA Checklist

- [x] Security reviewed (no new inputs; auth errors still surface immediately)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested (all attempts exhausted, auth, São Paulo midnight, unknown style)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-16 04:00

Implemented, benchmarked the fallback candidates on the prod endpoint, and ran the full unit suite plus the affected integration files.

## Files Touched

See Delta.

## Test Evidence

- Unit suite: 3967 passed before the contract updates; the 4 updated files then 36 passed, 0 failed.
- Integration on Postgres: `test_pov_inputs_acl.py` (11 passed), `test_autopilot_carousel_defaults.py` (11 passed).
- Static gates (changed-only): GATES_JSON {"pass":17,"fail":0,"skip":5}.

## QA Report

Pending (hotfix fast path: CI Test & Coverage decides).

## Decision Log

- 2026-10-16: Fallbacks are Qwen models on the same endpoint. `glm-5.3-flash` was the fastest, but the owner ruled out GLM.

## Blockers

None.

## Final Summary

Pending.
