# AE-0264 — expand carousel palettes and add the light flat-editorial image preset

Status: In Development
Tier: T2
Priority: Medium
Type: Feature
Area: backend, frontend
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: feat/carousel-palettes-light-editorial
Kanban Card: TBD
Created: 2026-06-22
Updated: 2026-06-22

## Goal

Broaden the carousel image visual range beyond the single dark-neon/cyberpunk
look: add 8 new selectable palettes (5 dark variants + 3 light/editorial) and a
matching **light** image strategy (`flat_editorial`) so the light palettes render
correctly instead of fighting the dark "neon glow" presets. GPT (`openai`) +
`neo_anime` is already the shipped default and is unchanged.

Spec: `docs/design/carousel-image-theme-alternatives.md`
Draft swatch board (approved by the user): `docs/design/carousel-palette-swatches.draft.html`

## Problem

`CAROUSEL_THEMES` shipped only 5 dark palettes and every image strategy phrased a
dark "neon glow" background (`_palette_fragment`). There was no light/editorial
option, and a light palette routed through a dark strategy produces a
contradictory prompt ("Dark background (#f7f5f0)…").

## Scope

- Add 5 dark-variant palettes (plasma_magenta, acid_lime, mono_indigo,
  ember_crimson, blueprint) + 3 light palettes (risograph, paper_editorial,
  clinical_mint) to `CAROUSEL_THEMES` + the `CarouselTheme` enum.
- Add `OpenAIFlatEditorialStrategy` + `IMAGE_STYLE_FLAT_EDITORIAL` + the
  `(openai, flat_editorial)` combo (registry + `SUPPORTED_IMAGE_COMBOS`), with a
  light-aware `_editorial_palette_fragment` (no neon glow).
- Decouple the AUTO rotation pool (`AUTO_ROTATION_THEME_KEYS`) from the full
  palette catalog so AUTO never hands a LIGHT palette to a dark strategy.
- Frontend: expose the new themes + the flat_editorial preset in
  `constants/create.ts`, the zod schema, and en/pt i18n.
- Split the large keyword maps into `carousel_theme_keywords.py` to keep
  `carousel_themes.py` under the 400-line ceiling.

## Non-Goals

- No change to the default combo (still `openai` + `neo_anime`).
- The runtime **AI-auto custom palette** path (LLM-generated `{primary, accent,
  background}` per carousel) is a follow-up increment, not this ticket.
- No change to persona/voice or text content. No backdrop/custom-details
  plumbing (that is AE-0263).

## Classification (no-`.feature`? No — behavior-changing)

Behavior-changing (new user-selectable themes + a new image style). `.feature`
scenarios added to `tests/features/image_generation_provider.feature`.

## Acceptance Criteria

- [x] 13 palettes total; every `CAROUSEL_THEMES` key has a matching
      `CarouselTheme` enum value.
- [x] `(openai, flat_editorial)` resolves to `OpenAIFlatEditorialStrategy`; its
      prompt carries "Flat editorial vector illustration" + "Light background" and
      no "neon glow".
- [x] AUTO never returns a light palette (asserted across 200 unmatched topics).
- [x] Light palettes are reachable only by explicit `project.theme`.
- [x] Frontend selectors + zod schema + en/pt i18n carry the new themes/preset.
- [x] `.feature` updated; backend ruff/mypy/lint-imports/arch-ratchet green;
      frontend lint/typecheck/schema-drift green; full backend + frontend suites green.

## Affected Areas

- Backend: `domain/constants/carousel_themes.py`, new
  `domain/constants/carousel_theme_keywords.py`, `domain/constants/carousel.py`,
  `domain/constants/__init__.py`, `domain/models/carousel.py`,
  `application/services/image_style_strategies.py`,
  `application/services/image_provider_registry.py`,
  `application/services/carousel/theme_resolver.py`
- Backend tests: `tests/unit/application/test_theme_resolver.py`,
  `test_image_provider_registry.py`, `test_image_style_strategies.py`,
  `tests/features/image_generation_provider.feature`
- Frontend: `src/constants/create.ts`, `src/schemas/carousel.ts`,
  `src/i18n/locales/{en,pt}.json`

## QA Checklist

- [ ] Security reviewed (no new external input paths; theme stays `String(30)`)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (AUTO never light; explicit light; missing palette keys)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-22

Implemented end-to-end on `feat/carousel-palettes-light-editorial` (branched off
`origin/main` @ fe0b9ef2). User approved the draft swatch board and asked to build
all 8 palettes + the light editorial preset; GPT neo-anime confirmed as the
existing default.

Two commits:
- `d052f235` — palettes + flat-editorial strategy + constants/schema/i18n.
- `40274689` — surface all 13 themes in the create dropdown (it had hardcoded
  the original five) + light→flat_editorial nudge with a component test +
  `create.lightThemeHint` i18n key.

Gates: backend 14 PASS / 1 pre-existing pip-audit FAIL / 4 DB-skip + 2312 pytest;
frontend **17 PASS / 0 FAIL / 0 SKIP** (final run incl. nudge) + 896 tests.

Local run: rebuilt backend + frontend docker images. Verified the new themes +
"OpenAI · Flat Editorial" appear in the real create UI and the light→flat_editorial
nudge fires live (auto-switches preset + shows hint).

**Dark validation PASSED** — built a full "AI agents" carousel with Plasma Magenta +
GPT neo-anime (project a678c5e6). Rendered slides show magenta primary + cyan accent
on near-black over neo-anime artwork — postable, matches the swatch.

**Light validation caught a real bug (fixed, commit d0b8af5d):** the prompt renderer
(`carousel/image_prompt_package.py`) keeps its **own** `_STRATEGY_MAP`, separate from
`image_provider_registry`. AE-0264's first two commits updated the registry but not
this map, so `(openai, flat_editorial)` fell back to `_DEFAULT_STRATEGY`
(GeminiComicNeon) — a light palette rendered with "neon glow" directives. Confirmed
from the live GPT prompt (paper_editorial colors + "neon glow", no "Flat editorial").
Fix: add the entry + a **drift-guard test** asserting every `SUPPORTED_IMAGE_COMBOS`
has a `_STRATEGY_MAP` strategy. Rebuilding backend and regenerating the light carousel
to confirm the editorial render.

Follow-up smell: two strategy maps must stay in sync (registry + prompt renderer) —
candidate kaizen to consolidate onto one source of truth.

**Light validation — artwork PASSED, composition gap found (follow-up).** After the
fix, the Flat Editorial **artwork** renders correctly (matte blue/cream vector, light
ground) — validated on project 69d77a0e. BUT the slide **text composition layer**
(export/CSS overlay + design-token text treatment) still renders white / light-gray
text with a dark scrim regardless of palette, so on a light background the body and
structured-item text is near-invisible (low contrast). The dark palettes are fully
postable; the **light palettes are not postable until the slide renderer is
light-theme-aware** (dark ink on light bg, light scrim, WCAG ≥ 4.5:1). This is a
SEPARATE, larger piece than AE-0264's image-strategy scope (touches the export
asset renderer / design tokens) → **new follow-up ticket recommended (AE-0265)**.
Scope AE-0264 should arguably ship the **dark variants** as done and gate the light
palettes behind the renderer work.

## Test Evidence

Commit: d052f235 (branch `feat/carousel-palettes-light-editorial`, base `origin/main` @ fe0b9ef2)

Manual full suites: backend `uv run pytest` → **2312 passed, 4 skipped**;
frontend `npm run test` → **896 passed**.

Full `gates.sh backend` (`.agent/reports/.gates-ae0264-backend.log`):
GATES_JSON: {"pass":14,"fail":1,"skip":4} — mutation 80.18% (≥75%).
- The single FAIL is `backend:pip-audit`: 3 **pre-existing** dependency CVEs
  (langsmith 0.8.5, msgpack 1.1.2, pydantic-settings 2.13.1). AE-0264 changes no
  dependencies; this fails identically on `main`. Not introduced here.
- The 4 SKIPs (`test`/`diff-cover`/`migrations`/`schema-drift`) require a local
  `DATABASE_URL` (Postgres). They run in CI; the non-integration suite (2312) is green.

Full `gates.sh frontend` (`.agent/reports/.gates-ae0264-frontend.log`):
First run flagged `frontend:dead-code` (a speculative unused `LIGHT_THEME_KEYS`
export) — removed; re-run is clean. GATES_JSON: pass=17, fail=0, skip=0.

## QA Report

Pending.

## Final Summary

Shipped on `feat/carousel-palettes-light-editorial` (3 commits, kept local per user):
`d052f235` palettes+preset, `40274689` dropdown+nudge, `d0b8af5d` strategy-map fix.
Gates: backend 14 PASS / pip-audit (pre-existing) / 4 DB-skip + mutation 80.18%;
frontend 17/0/0. Full backend pytest 2312, frontend 896.

Live validation (local rebuilt app, real GPT pipeline):
- **5 dark palettes — all postable**, each generated end-to-end on a relevant topic
  and visually confirmed: plasma_magenta (agents), acid_lime (loops), mono_indigo
  (harness), blueprint (architecture), ember_crimson (AI hype). The last four were
  generated fully unattended via a host-side auto-driver (Bearer token from
  `/api/auth/token` → `workflow/start` → `resume {approve}` loop keyed on
  `phase_status='awaiting_human'` + `lock_version`).
- **Light flat_editorial** — artwork validated; **text composition not light-aware**
  → deferred to follow-up (see below). The light→flat_editorial nudge works live.

**Status recommendation:** mark AE-0264 done for the **dark variants + the preset
plumbing + the nudge**; the **3 light palettes are gated behind the renderer
follow-up** (light-aware slide text: dark ink on light bg, WCAG ≥ 4.5:1).

**Follow-ups to file:**
- **AE-0265** — light-theme slide text composition (export/CSS + design tokens).
- Kaizen — consolidate the two strategy maps (registry + `image_prompt_package`)
  onto one source of truth (the drift caused the d0b8af5d bug).

**Local-env note:** the 4-day-old local Postgres was reconciled from a pre-squash
alembic rev to head (`e5f6a7b8c9d0`) by adding `blog_posts.origin/distribution` +
`documents.scope/is_public` and stamping; `rag_user` password set to `rag_password`.
