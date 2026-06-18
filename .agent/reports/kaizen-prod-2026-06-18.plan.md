# Kaizen Report — prod-2026-06-18
Mode: incident (production validation sweep) | Generated: 2026-06-18 | Signal window: live prod carousel run (project b5b61790)

Source: the production validation + carousel run on `marinssolutions.com`. These are
**failures observed live in prod that were left unfixed** (or only hot-patched for the
one carousel). Each proposal pairs the production fix with a **recurrence guard**
(test/gate/startup-check) so the failure class can't silently return — ratchet UP.

## Failure Classes (ranked by frequency × severity)

| # | Class | Freq | Sev | Gate that should have caught it | Status in prod |
|---|-------|------|-----|--------------------------------|----------------|
| FC-1 | **Prod DB schema drift** (create_all, no Alembic) | recurring (≥2×) | CRITICAL | deploy/startup "migrations applied & schema matches models" check | columns hot-patched; systemic cause OPEN |
| FC-2 | **Image-gen rate limit + too-short backoff** | every ≥6-slide carousel | HIGH | provider-limit-aware concurrency + 429 retry-after honoring | worked around manually; OPEN |
| FC-3 | **All-or-nothing image resume + stale `in_progress` lock** | every partial image failure | HIGH | partial-commit + always-release-lock; resume idempotency test | unstuck manually; OPEN |
| FC-4 | **Stuck-workflow backlog; no effective auto-reject** | 16+ live (48h) | MEDIUM | timeout → auto-reject/cleanup (CLAUDE.md rule) + alert | OPEN (alerts only warn) |
| FC-5 | **EN localization renders all-lowercase** headings/bodies | every carousel | MEDIUM | content/QA check: EN heading starts uppercase | data hot-patched for one; generator OPEN |
| FC-6 | **Swallowed worker exception** (`workflow_workers_error`, no traceback) | every 60s | MEDIUM | structlog renders exc_info; then fix underlying error | OPEN |
| FC-7 | **In-memory checkpointer in prod** (`CAROUSEL_CHECKPOINT_BACKEND=memory`) | always | MEDIUM | startup validation: prod must use durable backend | OPEN |
| FC-8 | **Missing frontend i18n keys** (`create.preview.previousSlide/nextSlide`) | every Review page | LOW | i18n completeness lint catches missing keys | OPEN |
| FC-9 | **`GEMINI_API_KEY` empty + default preset = Gemini** | any default-preset carousel | LOW | startup validation of configured image-provider keys | OPEN |

Minor (note, not ticketed): "6 images generated" vs 7 slides in the artifacts summary (cosmetic count).

## Proposals (ratchet UP) — proposed tickets

### P1 — FC-1 — Reconcile prod to Alembic + run migrations on deploy  [ratchet: UP] [T3, Backend/DevOps, ADR]
- Root cause (5-whys): prod was bootstrapped via `create_all`, has no `alembic_version`; `create_all` never ALTERs existing tables; deploy runs no migrations → every new model column silently 500s prod when first referenced (caught live twice: `caption_en`, then `origin`+`distribution`).
- Enforcement: introspect+reconcile prod schema, `alembic stamp` the matching baseline (depends on **AE-0086** self-contained chain), make `deploy.yml` run `alembic upgrade head`, add a startup/CI **schema-vs-models drift check** that fails the deploy if a model column is missing. ADR for the prod-migration policy.
- Files: `.github/workflows/deploy.yml`, `backend/alembic/*`, a new `scripts/ci/` drift check, `docs/decisions/NNNN-prod-migrations.md`. Relates AE-0086, AE-0127, AE-0204.

### P2 — FC-2 — Provider-rate-limit-aware image generation  [ratchet: UP] [T2, Backend]
- Root cause: 7 images fired in parallel against an org image cap of 5/min; retries (0.38s, 0.86s) far below the 429 `retry-after` (~12s).
- Enforcement: cap concurrency to the provider's documented limit (config), and on 429 back off by the returned `retry-after` (exponential, capped). Seeded test: a stubbed 429 → the runner waits and succeeds instead of failing the phase.
- Files: `infrastructure/external/openai_image.py`, `application/services/carousel/nodes/images.py`, settings. Relates AE-0017.

### P3 — FC-3 — Robust images-phase resume (partial commit + lock release)  [ratchet: UP] [T2, Backend]
- Root cause: one image's exception aborts the whole `_execute_background_resume`; successful images are never committed to workflow state (`image_assets` stays 0); `_mark_background_resume_failed` leaves `project.phase_status='in_progress'`, which `ensure_resume_not_in_progress` then 409-blocks → permanent stuck.
- Enforcement: commit per-slide successes (generation is already idempotent via `prompt_hash`); guarantee the `in_progress` lock is released to `failed`/`awaiting_human` on ANY failure; make the images phase re-entrant. Seeded test: inject a single-slide failure → other slides persist, lock releases, a retry completes.
- Files: `application/services/carousel/editorial_workflow_resume_runner.py`, `nodes/images.py`. Relates AE-0027, AE-0025.

### P4 — FC-4 — Enforce the "never leave workflows stuck" rule  [ratchet: UP] [T2, Backend]
- Root cause: CLAUDE.md mandates "Auto-reject after timeout; never leave workflows stuck", but the worker only emits `stuck_workflow` **warnings** — no transition. 16+ workflows sat at `brief/pending` for 48h.
- Enforcement: timeout → auto-reject/cancel (configurable) in the workflow worker; one-time cleanup of the existing backlog; metric/alert on count. Seeded test: a workflow past timeout is auto-transitioned.
- Files: `application/workers/workflow_workers.py`, `WorkflowFailureAlertService`. 

### P5 — FC-5 — EN localization casing fix + content gate  [ratchet: UP] [T2, Backend/Prompts]
- Root cause: the EN `translation_en` step emits all-lowercase `heading`/`body`; every carousel's EN slides render lowercase (PT is proper-case).
- Enforcement: fix the localization prompt (or post-process to sentence-case) so EN headings/bodies are properly capitalized; add a render/QA assertion that EN headings start uppercase. Seeded test: a lowercase EN heading is normalized/flagged.
- Files: `agents/prompts/carousel/v3/*.yaml` (localization), `application/services/carousel/...` localization step, a content check.

### P6 — FC-6 — Stop swallowing the worker traceback  [ratchet: UP] [T1, Backend/Observability]
- Root cause: `logger.exception("workflow_workers_error")` emits only the event (no stack) under the prod structlog config → undiagnosable; fires every 60s.
- Enforcement: configure structlog to render `exc_info`/traceback (or attach it to the event); then diagnose + fix the underlying scheduled-publish/reminders failure. Guard: a test asserting the logging config includes the exception renderer.
- Files: `infrastructure/logging.py`, `application/workers/workflow_workers.py`.

### P7 — FC-7 — Durable checkpointer in prod  [ratchet: UP] [T2, Backend/DevOps]
- Root cause: prod runs `CAROUSEL_CHECKPOINT_BACKEND=memory`; workflow state is lost on restart and not durable across processes, compounding resume fragility.
- Enforcement: set prod to `postgres` (code already supports it via `_build_checkpointer`, which runs `.setup()`); add a startup validation that warns/fails if a non-durable backend is used outside dev. Relates AE-0075.
- Files: deploy env/secrets, `bootstrap/app_factory.py` (startup check), `infrastructure/config/settings.py`.

### P8 — FC-8 — i18n completeness gate + the two missing keys  [ratchet: UP] [T1, Frontend]
- Root cause: `create.preview.previousSlide` / `create.preview.nextSlide` missing from the en locale → console errors + raw keys shown on the preview nav buttons.
- Enforcement: add the keys; add/extend an **i18n completeness lint** (every referenced key exists in every locale) wired into `npm run lint`. Seeded test: a referenced-but-missing key fails the lint.
- Files: `frontend/src/.../locales/en*.json`, a `frontend/scripts/check-i18n-*.mjs`, `package.json` lint chain.

### P9 — FC-9 — Validate image-provider config at startup  [ratchet: UP] [T1, Backend]
- Root cause: `GEMINI_API_KEY` is empty but "Gemini · Comic Neon" is the **default** image preset → a default-preset carousel would fail at image gen.
- Enforcement: validate that the configured/default image-provider has a key at startup (fail fast or disable that preset); or change the default to a provider with a key. Guard: a test that the default preset's provider key is required.
- Files: `infrastructure/config/settings.py`, image provider registry, the preset list.

## Rejected (would loosen the bar)
- None. (No proposal lowers a threshold or adds a suppression; lazy-loading "broken images" was a non-issue and is excluded.)

## Phase 3.5 — Independent skeptical review (cold-critic) + corrections applied
An architect cold-critic verified all 9 against live code + prod (read-only). Invariant re-validated: no proposal loosens a gate. Corrections folded into the tickets:
- **P2**: the 0.38s/0.86s retries are the OpenAI SDK's internal `max_retries`, NOT app code (none exists) — scope = concurrency cap + retry-after.
- **P3**: the stale-`in_progress`-lock claim was FALSE (`_mark_background_resume_failed` already sets `failed`, AE-0027) — re-scoped to `asyncio.gather` partial-commit + idempotent re-entry.
- **P5**: EN validation + repair already exist & are blocking — re-scoped to a render-source (`translation_en`) gap + regression test.
- **P6**: structlog `format_exc_info` is configured and works — re-rooted to the `workflow_workers.py:53` call site.
- **P8**: the two keys already exist on main (prod is a stale build → redeploy) — kept only the i18n-completeness lint.

## Tickets created (Phase 5)
- AE-0207 — Reconcile prod DB to Alembic + run migrations on deploy (T3, Critical)
- AE-0208 — Provider-rate-limit-aware image generation (T2, High)
- AE-0209 — Per-slide partial-commit + idempotent re-entry for images phase (T2, High)
- AE-0210 — Enforce never-stuck workflows: timeout auto-reject + cleanup (T2, High)
- AE-0211 — Verify EN sentence-case repair covers translation_en render source (T1, Medium)
- AE-0212 — Emit traceback for workflow_workers_error (T1, Medium)
- AE-0213 — Durable LangGraph checkpointer in prod (postgres) + startup guard (T2, Medium)
- AE-0214 — i18n completeness lint (T1, Low)
- AE-0215 — Validate default image-provider key at startup (T1, Medium)
