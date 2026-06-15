# Phase 5 — Extract Carousel Presentation (epic plan)

**Planner output.** Source: `.agent/reports/domain-modularization.options.md` §"Phase 5" (lines 989-1024).
Builds on merged Phases 0-4 (`modules/{knowledge,identity,conversation,editorial}` live; the editorial module
owns the carousel WORKFLOW slice behind a facade + `LegacyCarouselAcl` + `CarouselProjectWriteOwner`).
**Precondition: Phase 4 (PR #18) merged.** Reuses the AE-0081 conventions, `modules/_template`, the
`platform/database` UoW, the QA-guardian gates, and the AE-0103/AE-0112 import-contract + baseline-ratchet pattern.

## Goal

Extract a `presentation` bounded context — slides, design/theming, layout strategies, presentation policy +
validation, rendering, image generation (+ providers as adapters), artifact build/activation, and export —
behind a public facade. The editorial workflow invokes presentation **through a port/public facade**.
**Behavior-preserving**: presentation response schemas (CarouselDesignResponse, CarouselBlogResponse/i18n,
CarouselSlideResponse, StrategyListResponse, CreatorAssetResponse), artifact URLs, `FileResponse` bytes/headers
(PDF/JPEG), and the `artifact_version`↔`lock_version` activation CAS stay byte-identical. **NO renames.**

## Scope boundary (roadmap exit gate)

**Presentation OWNS:** slide rows (CarouselSlideModel); the carousel_projects PRESENTATION columns
(`design_tokens`, `output_dir`, `pdf_path`/`pdf_path_en`, `artifact_version`, `slide_layout_strategy`,
`presentation_policy_version`/`checksum`, `title`/`subtitle`/`*_en`, `primary/accent/background_color`,
`creator_*` watermark); design/theming; layout strategies; presentation policy + validation; image generation
(+ OpenAI/Gemini providers as port adapters); artifact build/activation; export/rendering; creator assets.

**Presentation does NOT own** (roadmap): blog (`blog_markdown`/`blog_translations`), distribution
(`caption*`, `linkedin_post_*`), publishing/`is_public`, persona, or workflow state — those are **Phase 6
(distribution/publishing)** or editorial (workflow). The Phase-5 module exposes what carousel needs; it does
not extract distribution.

## Reality vs. spec (2026-06-15 code scan)

- **Routes:** `api/routes/carousels/{media,preview,strategies,admin,creator_assets}.py` (+ presentation parts of
  `crud.py` GET/publish). Media/preview return `FileResponse` (PDF/JPEG) + design/blog/slide schemas — byte-identical
  is bytes+headers, not just JSON.
- **Services:** ~30 presentation files under `application/services/carousel/`: artifact build/activation
  (`artifact_build_service.py` + support/types/health/manifest/path_resolver/path_safety/index_reconciler),
  design/theming (`design_token_utils.py`, `theme_resolver.py`, `nodes/design.py`), image gen
  (`nodes/images.py`, `image_generation_records.py`, `image_prompt_package.py`, `image_validation.py`,
  `image_provider_registry.py`), export/rendering (`nodes/export.py`, `carousel_export_assets.py`,
  `carousel_template/`, `localized_slide_builder.py`), policy/validation (`presentation_policy*.py`,
  `presentation_review*.py`, `presentation_validation*.py`, `visible_copy_sanitize.py`), creator assets.
- **`artifact_version` CAS:** `carousel_artifact_build_repository.activate_build` bumps `artifact_version`
  **paired with `lock_version`** (AE-0105 §4) — shared with the editorial resume CAS. Phase 5 MUST preserve the
  pairing exactly (coordinate with the AE-0107 `CarouselProjectWriteOwner`).
- **Image providers:** `image_provider_registry.resolve(model, style)` → provider; concrete `OpenAIImageService`
  (`infrastructure/external/openai_image.py`) + Gemini. Become `ImageProviderPort`/`ImageGenerationService` adapters.
- **Editorial → presentation coupling:** `editorial_finalize.py:197-202` calls the artifact builder + sets
  `pdf_path*`; the design/images/export workflow nodes are presentation ops invoked by the editorial workflow;
  `nodes/images.py:381-390` writes `phase_progress` (workflow state) — needs a presentation→editorial callback port.
- **Sequencing:** AE-0045 (presentation_review Chain-of-Responsibility) + AE-0046 (carousel_presentation
  ContentSlideCopy validators) are PASS QA / in Review and touch presentation files — Phase 5 builds on them
  (must merge before the route/file movement in Wave C/D; do not re-refactor).

## Ticket breakdown

| ID | Title | Tier | Area | Blocked by |
|----|-------|------|------|------------|
| **AE-0114** | Phase 5 epic: Extract Carousel Presentation | T3 | Cross-cutting | — (tracks 0115-0122) |
| **AE-0115** | Presentation field/surface ownership map (extends AE-0105: columns, slide rows, node boundary, artifact_version↔lock_version CAS) | T2 | Docs/Arch | — |
| **AE-0116** | Presentation byte-identical safety net (media/preview/slides/design/strategies/creator-asset responses + FileResponse bytes/headers + artifact URLs; deterministic image-provider stub) | T2 | Tests | — |
| **AE-0117** | `modules/presentation/` skeleton + facade + bootstrap + domain (PresentationProject/DesignPolicy/SlideView + policy types) + re-exported ports | T2 | Backend | — |
| **AE-0118** | Presentation persistence: single writer/ACL for presentation columns + slide rows; preserve artifact_version↔lock_version CAS pairing | T2 | Backend | AE-0115, AE-0116, AE-0117 |
| **AE-0119** | Image-provider ports + adapters (ImageProviderRegistry + OpenAI/Gemini behind ImageProviderPort / ImageGenerationService) | T2 | Backend | AE-0117 |
| **AE-0120** | Presentation routes (media/preview/slides/strategies/design/creator-assets) behind presentation handlers via facade (byte-identical) | T2 | Backend | AE-0116, AE-0117, AE-0118, AE-0119 |
| **AE-0121** | Artifact build + export/rendering + design + policy/validation/review behind presentation contracts; editorial workflow invokes presentation via a PORT (design/images/export + finalize artifact build; carousel_workflow_nodes repointed); phase_progress callback; ContentFormatProducer extension point | T2 | Backend | AE-0118, AE-0119, AE-0120 (+ AE-0045/0046 merge) |
| **AE-0122** | Presentation import contracts + exit gate + baseline ratchet + docs | T2 | Backend/CI | AE-0120, AE-0121 |

## Suggested order (waves)

- **Wave A (parallel):** AE-0115 (field map), AE-0116 (safety net), AE-0117 (presentation skeleton).
- **Wave B (parallel):** AE-0118 (presentation persistence/ACL — needs 0115/0116/0117), AE-0119 (image-provider ports — needs 0117).
- **Wave C:** AE-0120 (presentation routes behind handlers — needs 0116/0117/0118/0119). *Gate: AE-0045/0046 merged.*
- **Wave D:** AE-0121 (artifact/export/design + presentation policy/validation/review behind contracts; carousel_workflow_nodes repointed via the editorial→presentation port + ContentFormatProducer — needs 0118/0119/0120). *Gate: AE-0045/0046 merged.*
- **Wave E:** AE-0122 (import contracts + exit gate + ratchet — needs 0120/0121).

## Risks & guardrails

- **Presentation API byte-identical incl. binary artifacts.** Mitigation: AE-0116 snapshots design/blog/slide
  JSON responses AND asserts `FileResponse` content-type/headers/bytes for PDF/JPEG endpoints + artifact URL
  strings; uses a DETERMINISTIC image-provider stub (no live DALL-E/Gemini — no API keys in this env); AE-0120/0121
  gated on diff=0. Build on the existing test_media_access.py.
- **`artifact_version`↔`lock_version` CAS pairing.** AE-0118/0121 preserve `activate_build`'s compare-and-swap and
  its pairing with the editorial resume CAS EXACTLY — coordinate with the AE-0107 `CarouselProjectWriteOwner`; no
  concurrency-token change. (Mirrors the Phase-4 lock_version constraint.)
- **Editorial→presentation port (no circular dependency).** Editorial invokes presentation via a port/facade
  (design/images/export + artifact build); the `nodes/images.py` `phase_progress` write becomes a
  presentation→editorial callback port — keep the dependency direction editorial→presentation (presentation does
  not import editorial internals).
- **god-row shared persistence.** `carousel_projects` stays one table; presentation owns its columns via an ACL/
  single-writer; distribution columns (blog/caption/linkedin) stay shared (Phase 6). No renames.
- **Image providers need no live keys in tests.** Providers behind ports; tests stub them. CI has no image API keys.
- **Checkpoint-drain rule (from Phase 4).** No schema-modifying migration while a live LangGraph checkpoint
  references the old shape — encoded in AE-0122 + the epic exit gate. Phase 5 is structured to need no migration.
- **Don't double-refactor.** AE-0045/0046 already refactored presentation_review/carousel_presentation — build on
  them; they must merge before Wave C/D file movement (or Phase 5 owns the current state).

## Epic exit gate (from the plan)

- Carousel **means presentation only** (the presentation module owns slides/design/render/artifact/export).
- Editorial workflow invokes presentation **through a port/public facade** (no direct presentation-internal calls).
- Presentation does **not** own blog, publishing, persona, or workflow state.
- Presentation response schemas + artifact URLs + FileResponse bytes byte-identical (AE-0116 snapshots diff=0).
- `artifact_version`↔`lock_version` CAS pairing + LangGraph checkpoints preserved; checkpoint-drain rule documented.
- `gates.sh` + `check-integrity` green; `presentation-application-isolation` + `presentation-public-facade` import
  contracts KEPT; AE-0082 baseline ratcheted down (or held); module-conventions §12 documents presentation.

## Handoff

→ `/architect-skill` validate loop (confirm AE-0114-0122 Ready), then execute Waves A→E with the developer-skill +
QA-guardian loop, exactly as in Phases 2-4. Gate Wave C/D on AE-0045/0046 merge.
