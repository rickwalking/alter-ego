# AE-0308 — re-route comic_neon image preset to openai provider (gemini unfunded in prod)

Status: Review
Tier: T2
Priority: High
Type: Bugfix
Area: fullstack
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0308-comic-neon-openai-reroute
Kanban Card: TBD
Created: 2026-07-02
Updated: 2026-07-02

## Goal

The Comic Neon image style generates via the OpenAI image provider, and no selectable
preset (or persisted default) can route a carousel to a provider whose API key is not
configured. Prod intentionally has no `GEMINI_API_KEY` — all image generation targets
GPT (user decision, 2026-07-01).

## Problem

`(gemini, comic_neon)` is the ONLY Gemini combo in `SUPPORTED_IMAGE_COMBOS`, and the
`gemini__comic_neon` preset is the FIRST option in the create UI. Prod has no
`GEMINI_API_KEY` **by design**, so any carousel created with that preset burns through
research/outline/content (minutes of LLM spend + a human design approval) and then fails
ALL slides at the images phase with `RuntimeError: Gemini API key is not configured`
(observed in prod 2026-07-02, carousel `a3082cf2`; recovered by hand-flipping the DB row
to `openai/neo_anime` and resuming).

AE-0215 fixed only the *application default* (`IMAGE_MODEL_DEFAULT = openai`); it left
three other paths to the broken provider:

1. The UI preset `gemini__comic_neon` (`frontend/src/constants/create.ts`).
2. DB `server_default="gemini"` / `"comic_neon"` on `carousel_projects`
   (`infrastructure/database/models/carousel.py:58-59`).
3. 12 legacy prod rows on dead combos: 11 × `gemini-2.5-flash-preview-05-20/neon_comic`
   (pre-rename values, resolve as unsupported) and 1 × `gemini/cinematic` (never in
   `SUPPORTED_IMAGE_COMBOS`) — any image re-run/refinement on these fails.

The comic-neon prompt itself (`GeminiComicNeonStrategy.wrap`) is provider-agnostic pure
text, so the style can move providers without changing its visual identity.

## Scope

- **Backend re-key** `(gemini, comic_neon)` → `(openai, comic_neon)` in the three maps
  that must stay in sync:
  - `domain/constants/carousel.py` → `SUPPORTED_IMAGE_COMBOS`
  - `application/services/image_style_strategies.py` → `IMAGE_STRATEGY_REGISTRY`
    (rename `GeminiComicNeonStrategy` → `OpenAIComicNeonStrategy`)
  - `application/services/carousel/types.py` → `IMAGE_PRESET_DISPLAY`
    (label → "OpenAI Comic Neon")
- **Prompt parity**: add the brand/likeness STRICT block used by the other OpenAI
  strategies (no real-world brands, logos, celebrity/CEO likenesses) to the comic-neon
  prompt; keep the rest of the prompt text byte-identical.
- **DB defaults**: `server_default` on `carousel_projects.image_model` → `"openai"`
  (style default `comic_neon` stays valid once re-keyed). Note prod DB is create_all
  bootstrapped — the model change alone does not alter the live column default; include
  it in the data-repair script.
- **Data repair (prod)**: one idempotent script normalizing legacy rows to supported
  combos: `gemini-2.5-flash-preview-05-20/neon_comic` → `openai/comic_neon`;
  `gemini/*` → `openai/*` (style unchanged when supported). Completed carousels keep
  their rendered images on disk — the repair only changes what a future re-run resolves.
- **Fail-fast guard (systemic)**: project creation returns 422 when the requested
  `(image_model, image_style)` resolves to a provider whose API key is not configured
  (extends the AE-0215 default-combo guard to *all* requested combos), so a future
  unfunded provider fails at creation, not after minutes of pipeline work.
- **Frontend**: preset value `gemini__comic_neon` → `openai__comic_neon` with
  `model: openai` (`constants/create.ts`); i18n label `imagePresets.openai_comic_neon`
  ("OpenAI · Comic Neon") in `en.json` + `pt.json`; Zod supported-combo list in
  `schemas/carousel.ts:130` re-keyed.
- **Tests/artifacts**: update `palette-drift.test.ts` and any snapshot/pinned artifacts
  that embed the combo; verify `docs/architecture/openapi.json`, route snapshot, and
  publishing goldens for drift (regenerate only if the contract actually changed).

## Non-Goals

- Funding Gemini / adding `GEMINI_API_KEY` to GitHub Secrets.
- Removing the Gemini provider service, `IMAGE_MODEL_GEMINI` constant, or the
  `gemini_image.py` infrastructure (stays dormant for future re-enable).
- New image styles, palette changes, or altering the comic-neon visual identity.
- Alembic adoption for prod (tracked separately; the repair script handles this drift).

## Acceptance Criteria

- [x] `SUPPORTED_IMAGE_COMBOS`, `IMAGE_STRATEGY_REGISTRY`, and `IMAGE_PRESET_DISPLAY`
      all key comic_neon under `openai`; no `(gemini, *)` combo remains supported.
- [x] `ImageProviderRegistry.resolve("openai", "comic_neon")` returns the OpenAI service
      paired with the comic-neon strategy; `resolve("gemini", "comic_neon")` raises
      `ValueError` (unsupported).
- [x] Comic-neon prompt output is unchanged except the inserted OpenAI brand/likeness
      STRICT block (characterization test pins the wrap output; see Decision Log on
      placement).
- [x] Project creation with a combo whose provider key is unconfigured returns 422 with
      a clear error code (no workflow rows created); creation with `openai/comic_neon`
      succeeds when `OPENAI_API_KEY` is set. (Production-like envs; dev/test tolerate —
      see Decision Log.)
- [x] `carousel_projects.image_model` server default is `openai` (model + postgres
      ALTER in the repair script for the live create_all column).
- [x] Data-repair script is idempotent, logs each row it changes, maps
      `gemini-2.5-flash-preview-05-20/neon_comic` → `openai/comic_neon` and
      `gemini/<style>` → `openai/<style>`, and is safe to run on the live prod DB.
- [x] UI create flow offers `openai__comic_neon` (en + pt labels); `gemini__comic_neon`
      no longer exists; FE Zod combo validation accepts the new pair and rejects the old.
- [x] Full `gates.sh backend` + `gates.sh frontend` green (backend 15 PASS + 4
      Postgres/Docker SKIPs with full SQLite suite compensating: 2539 passed;
      frontend 17/17 PASS); pinned artifacts: only `palettes.json` changed.

## Gherkin Scenarios

```gherkin
Feature: Comic Neon carousels generate images via the OpenAI provider

  Scenario: Creating a Comic Neon carousel in prod completes the images phase
    Given prod has OPENAI_API_KEY configured and no GEMINI_API_KEY
    And a user creates a carousel with the "OpenAI · Comic Neon" preset
    When the workflow reaches the images phase
    Then all slide images are generated by the OpenAI image service
    And the phase-progress label reads "OpenAI Comic Neon"

  Scenario: Creation fails fast when the requested provider is unfunded
    Given GEMINI_API_KEY is not configured
    When a client POSTs a project with image_model "gemini" and any style
    Then the API responds 422 before any workflow phase runs
    And the error identifies the unconfigured provider

  Scenario: Legacy Gemini rows are repaired for future re-runs
    Given a prod row with image_model "gemini-2.5-flash-preview-05-20" and style "neon_comic"
    When the data-repair script runs twice
    Then the row reads image_model "openai" and image_style "comic_neon" after each run
    And previously rendered images on disk are untouched

  Scenario: Comic Neon visual identity is preserved across the provider move
    Given the same scene text and theme palette
    When the comic-neon strategy wraps the prompt
    Then the output matches the pre-move prompt plus only the brand/likeness STRICT block
```

## Delta

### ADDED

- `OpenAIComicNeonStrategy` (renamed from `GeminiComicNeonStrategy`, + brand STRICT block)
- Creation-time provider-key fail-fast guard (all combos, not just the default)
- Idempotent prod data-repair script for legacy gemini/neon_comic rows
- i18n keys `imagePresets.openai_comic_neon` (en, pt)

### MODIFIED

- `SUPPORTED_IMAGE_COMBOS`, `IMAGE_STRATEGY_REGISTRY`, `IMAGE_PRESET_DISPLAY` (re-key)
- `carousel_projects.image_model` server default → `openai`
- `frontend/src/constants/create.ts` preset entry; `frontend/src/schemas/carousel.ts` combos
- `palette-drift.test.ts` and affected snapshots/pinned artifacts

### REMOVED

- `(gemini, comic_neon)` from all combo maps; `gemini__comic_neon` preset + i18n keys

## Affected Areas

- Backend: domain constants, image strategy registry, provider registry, creation validation
- Frontend: create-flow presets, Zod carousel schema, i18n locales
- Database: `carousel_projects` column default; prod data repair (12 rows)
- API: creation 422 on unfunded provider (contract addition)
- Tests: strategy characterization, registry resolve, creation guard, FE schema/palette-drift
- Docs: none beyond ticket; verify openapi.json for drift
- Prompts/LLM: comic-neon wrap gains OpenAI brand-safety block
- Observability: image-gen traces will report provider `openai` for comic_neon
- Deployment: repair script must run against prod DB post-deploy (manual step, documented)

## Dependencies

- Blocks: —
- Blocked by: —
- Related: AE-0215 (default-combo guard), AE-0263 (brand-locked image style),
  memory `prod-no-gemini-key-by-design` (incident 2026-07-02, carousel `a3082cf2`)

## Implementation Plan

1. Re-key the three backend maps + rename strategy; pin prompt with a characterization test.
2. Extend the AE-0215 guard to validate the requested combo's provider key at creation (422).
3. Flip the DB server default; write + test the idempotent repair script (SQLite + a
   seeded-legacy-rows test).
4. Update FE preset/schema/i18n; fix palette-drift and snapshot tests.
5. Full gates both scopes; regenerate pinned artifacts only on real contract drift.
6. Post-deploy: run the repair script on prod; verify with the combo-count query.

## QA Checklist

- [x] Security reviewed (bandit + pip-audit PASS; guard reviewed externally)
- [x] Code quality reviewed (ruff/mypy strict/strict-diff/arch-ratchet PASS; external R1)
- [x] Acceptance criteria validated (every `[x]` independently re-verified, cold context)
- [x] Edge cases tested (Gherkin completeness dimension: every scenario maps to a real test)
- [x] Orphan/unfinished code checked (integrity 0/0 both scopes; dead-code gates PASS)

## Progress Log

### 2026-07-02 11:30

Development complete on `feat/ae-0308-comic-neon-openai-reroute` (5 commits, branched
from post-PR-#80 main). All backend + frontend changes implemented per plan; full
gates running. Targeted suites green: strategy/registry/preset-api (64), guard (8),
repair script (7), FE schema+palette-drift+create-page (137+). openapi.json verified
no-drift; route snapshot passes; arch-ratchet passes (guard lives in
`api/dependencies/feature_flags.py`, an existing settings edge — no new api→infra pair).

### 2026-07-02 01:30

Ticket created from the prod incident on carousel `a3082cf2-c9f0-4da4-8e33-e11d6172de2d`
(all 6 slides failed at images with "Gemini API key is not configured"; recovered by
flipping the row to `openai/neo_anime` and resuming — 6/6 generated, now in final_review).
Prod combo census taken: 13 openai/neo_anime, 11 legacy gemini-2.5-flash/neon_comic,
2 openai/hyperreal, 1 gemini/cinematic, 1 openai/cinematic.

## Files Touched

- `backend/src/rag_backend/domain/constants/carousel.py` — combo re-key, guard error constant
- `backend/src/rag_backend/domain/constants/__init__.py` — export `ERR_IMAGE_PROVIDER_UNCONFIGURED`
- `backend/src/rag_backend/application/services/image_style_strategies.py` — `OpenAIComicNeonStrategy` (+brand block), registry re-key
- `backend/src/rag_backend/application/services/carousel/image_prompt_package.py` — default strategy rename
- `backend/src/rag_backend/application/services/carousel/types.py` — `IMAGE_PRESET_DISPLAY` re-key ("OpenAI Comic Neon")
- `backend/src/rag_backend/infrastructure/config/settings.py` — `image_provider_api_key` (single provider→key map)
- `backend/src/rag_backend/bootstrap/startup_validation.py` — delegates to the shared map
- `backend/src/rag_backend/api/dependencies/feature_flags.py` — `require_image_provider_configured` (422 guard)
- `backend/src/rag_backend/api/routes/carousels/crud.py` — guard wired via route `dependencies=[...]`
- `backend/src/rag_backend/infrastructure/database/models/carousel.py` — server default → openai
- `backend/scripts/repair_image_provider_combos.py` — NEW idempotent repair (+postgres column-default ALTER)
- `backend/tests/features/image_generation_provider.feature` — default + AE-0308 scenarios
- `backend/tests/features/carousel_image_provider_reroute_ae0308.feature` — NEW guard + repair scenarios
- `backend/tests/unit/application/test_image_style_strategies.py` — rename + characterization pin
- `backend/tests/unit/application/test_image_provider_registry.py` — re-key + service-pairing test
- `backend/tests/unit/modules/presentation/test_image_provider_ports.py` — re-key
- `backend/tests/unit/api/test_image_provider_guard.py` — NEW guard unit + HTTP tests
- `backend/tests/unit/scripts/test_repair_image_provider_combos.py` — NEW repair tests (SQLite)
- `backend/tests/integration/test_image_preset_api.py` — accept openai/comic_neon, reject gemini/comic_neon
- `frontend/src/constants/create.ts` — `openai__comic_neon` preset
- `frontend/src/schemas/carousel.ts` — Zod combo re-key
- `frontend/src/schemas/carousel.test.ts` — accept/reject tests
- `frontend/src/i18n/locales/{en,pt}.json` — `imagePresets.openai_comic_neon`
- `docs/contracts/palettes.json` — regenerated (5 presets, comic_neon under openai)

## Test Evidence

- Backend full suite (SQLite): `uv run pytest tests/unit tests/integration -q`
  → **2539 passed, 4 skipped** (compensates the 4 Postgres/Docker gate SKIPs).
- Targeted AE-0308 suites: strategies + registry + ports + preset API + guard +
  repair script → **81 passed** (incl. characterization pin, service-identity,
  guard 422/tolerance, repair idempotency + dry-run).
- Frontend: `npx vitest run` schema + palette-drift + use-carousel → **64 passed**;
  full `frontend:test` gate PASS (whole suite) in the capture log.
- Gates: backend `GATES_JSON {"pass":15,"fail":0,"skip":4}` /
  frontend `GATES_JSON {"pass":17,"fail":0,"skip":0}`
  (`.agent/reports/.gates-capture-{backend,frontend}.log`); integrity 0 net-new
  both scopes; `export_openapi.py --check` clean; route snapshot passes.
- Full evidence: `.agent/reports/AE-0308.dev-summary.md`.

## QA Report

External GLM 5.2 (opencode-go, cold context), 2026-07-02: **QA_VERDICT: PASS**.
R1 read-only — all dimensions clean, 0 findings; R1b gate reproduction — the
reviewer ran both gate suites, both integrity scans, `export_openapi --check`,
AND the compensating 2539-test SQLite suite itself (all green; mutation 79.91%
backend / 84.82% frontend). One minor non-actionable finding (unreachable
mutant, schema-guarded). Full report + provenance:
`.agent/reports/AE-0308.qa.md`.

```
GATES_JSON: {"pass":15,"fail":0,"skip":4,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:test","status":"SKIP"},{"gate":"backend:diff-cover","status":"SKIP"},{"gate":"backend:migrations","status":"SKIP"},{"gate":"backend:schema-drift","status":"SKIP"},{"gate":"backend:mutation","status":"PASS"}]}
GATES_JSON: {"pass":17,"fail":0,"skip":0,"results":[{"gate":"frontend:lint","status":"PASS"},{"gate":"frontend:lint-changed","status":"PASS"},{"gate":"frontend:component-types","status":"PASS"},{"gate":"frontend:duplication","status":"PASS"},{"gate":"frontend:dead-code","status":"PASS"},{"gate":"frontend:typecheck","status":"PASS"},{"gate":"frontend:build","status":"PASS"},{"gate":"frontend:legacy-guard","status":"PASS"},{"gate":"frontend:legacy-inventory","status":"PASS"},{"gate":"frontend:format","status":"PASS"},{"gate":"frontend:security","status":"PASS"},{"gate":"frontend:integrity","status":"PASS"},{"gate":"frontend:test","status":"PASS"},{"gate":"frontend:schema-drift","status":"PASS"},{"gate":"frontend:duplication-tests","status":"PASS"},{"gate":"frontend:dead-files","status":"PASS"},{"gate":"frontend:mutation","status":"PASS"}]}
```

## Decision Log

- 2026-07-02: User confirmed the missing Gemini key is intentional — all prod image
  generation targets GPT. Re-route the style rather than fund the provider.
- 2026-07-02: Brand/likeness block is INSERTED after the existing STRICT sentence
  (sibling-consistent position), not appended at the end — the Gherkin "plus only the
  brand block" contract holds; the characterization test pins exact placement.
- 2026-07-02: The creation guard tolerates missing keys in dev/test (mirrors the
  AE-0215 startup-guard policy) — otherwise every keyless local run and stubbed
  integration test would 422 on create. Production-like envs reject.
- 2026-07-02: Side effect accepted: comic_neon prompts now pass through
  `sanitize_image_prompt` (the pipeline sanitizes all `image_model == openai`
  projects) — consistent with every other OpenAI preset.
- 2026-07-02: Guard placed in `api/dependencies/feature_flags.py` (existing
  api→infrastructure settings edge) and the provider→key map on `Settings`
  itself — zero new arch-ratchet pairs; startup guard delegates to the same map.

## Blockers

None.

## Final Summary

Pending.
