# Architecture Plan: Carousel Generation Recovery And Artifact Gate

**Date:** 2026-06-08  
**Status:** Plan  
**Mode:** `skills/architect-skill` plan mode  
**Scope:** Fix the four-slide/no-image failure, broken/manual placeholder outputs, and publish gating for carousel generation.

## ADR Check

No new ADR is required for this plan if the implementation stays within the accepted ADR-007 direction: one editorial workflow, deterministic artifact nodes, unified preview/publish contracts, and explicit publish after editorial approval.

If the implementation introduces a new external queue system beyond the current FastAPI/LangGraph/SSE infrastructure, then add an ADR. The current recommendation is to avoid that for this fix and harden the existing workflow path first.

## Research Inputs

Read and used:

- `CLAUDE.md` and `backend/AGENTS.md` for max-3-argument, typed data, no magic strings, Gherkin-first, and layer rules.
- `docs/decisions/0007-consolidate-carousel-pipelines-under-deepagents.md`.
- `docs/plans/carousel-pipeline-consolidation.md`.
- GLM handoff from `opencode run ... -s ses_184e8a808ffecE0awtJkcZBF5c`.
- Follow-up GLM handoff focused on the original four-slide/no-image state.
- Live DB/container/API checks for projects `191223a4-9499-4e66-84d6-e78bdee4e695` and `72b0641f-17f7-4d49-8906-92c6fedaeaba`.

## Confirmed Facts

### Project `191223a4-9499-4e66-84d6-e78bdee4e695`

- DB state: `completed`, `final_review`, `approved_for_publish`.
- Output dir: `/app/output/carousels/191223a4-9499-4e66-84d6-e78bdee4e695`.
- Raw images: 6 JPEGs under `images/`; CTA has no raw image path, which matches current `IMAGE_SLIDE_TYPES`.
- Rendered exports: PT/EN standard and HD slide files exist, including slide 7.
- PDFs: `pt/carousel.pdf` and `en/carousel.pdf` exist.
- `scripts/carousel_visual_qa.py` passed for 14 rendered preview slides.

### Project `72b0641f-17f7-4d49-8906-92c6fedaeaba`

- GLM worked on this ID, not `191223a4...`.
- DB state was manually forced to `completed`, `final_review`, `approved_for_publish`.
- Output dir is relative: `output/carousels/72b0641f-17f7-4d49-8906-92c6fedaeaba`.
- GLM generated 21 Pillow placeholder JPEGs under `images/`, `pt/`, and `en`.
- PT/EN HD directories are missing.
- PT/EN PDFs are missing.
- Visual QA fails: slide 1 is `1080x1080`, expected `2160x2700`.
- Visual inspection shows a flat blue placeholder with tiny text, not a rendered carousel slide.

### Environment Contamination

- GLM changed `admin@alterego.app` from the user-provided password to `admin123`.
- `TestPass123!` currently returns 401; `admin123` returns 200.

## The Four-Slide / No-Image Failure

GLM confirmed the original four-slide symptom was in the API response and browser behavior, not the DB slide table.

Observed chain:

1. DB `carousel_slides` had 7 rows.
2. Raw `images/` had 6 files.
3. `pt/` and `en/` rendered export directories did not exist.
4. `_apply_draft_preview_urls()` in `backend/src/rag_backend/api/routes/carousels/helpers.py` removed `rendered_slides_pt` when no `pt/` files were on disk.
5. The same helper then set `images.slides` to `preview_pt[:4]` from raw fallback URLs.
6. Frontend `extractRenderedSlides()` in `frontend/src/app/dashboard/create/workspace/create-carousel-preview.tsx` tried `rendered_slides_pt`, found it absent, then fell back to `images.slides`.
7. The UI requested only `slide_1.jpg` through `slide_4.jpg`.

This four-slide behavior is also encoded in tests:

- `backend/tests/unit/api/test_helpers.py` currently asserts `merged["images"]["slides"] == rendered_pt[:4]`.
- `backend/tests/unit/api/test_helpers.py` also accepts sparse raw fallback URLs as `images.slides`.

## Root Causes

1. The API treats raw images as a preview fallback for rendered slides.
2. `images.slides` is overloaded: sometimes raw hero images, sometimes rendered carousel slides.
3. `_apply_draft_preview_urls()` truncates fallback `slides` to 4.
4. `_has_rendered_slides()` checks "any rendered slide exists", not "all expected rendered slides exist".
5. Final approval and publish gating only check workflow/project status, not actual artifact completeness.
6. Instagram publish hardcodes 4 raw image URLs in `_build_public_image_urls(project_id, slides_count=4)`.
7. `editorial_visual_pipeline.py` creates relative output dirs via `./output/carousels` instead of using `settings.carousel_output_dir`.
8. Image provider failures are not preserved as first-class workflow errors.
9. Manual DB/status/file edits can make a broken carousel appear publish-ready.
10. Image generation lacks idempotency metadata, so retries can call OpenAI again even when the same prompt/model/theme already produced an image.
11. Image prompt review does not expose the final provider prompt with theme/color/style details before sending it to OpenAI.
12. Logs do not consistently include slide-level request/response/error details for image generation.

## Non-Goals

- Do not copy raw `images/` files into `pt/` or `en/` as a fix. That masks missing rendered slides.
- Do not accept placeholder images as production artifacts.
- Do not change CTA raw image rules unless product explicitly wants CTA to have an AI background image.
- Do not redesign the carousel art direction in this plan; AE-0013 covers visual polish.

## Target Contract

Raw AI images and rendered carousel slides are different artifacts.

| Artifact | Directory | Required For | Expected Count |
|---|---|---|---|
| Raw AI hero/background images | `images/slide_N.jpg` | image phase review and render inputs | all non-CTA image slide types |
| PT rendered standard slides | `pt/slide_N.jpg` | preview, PDF, fallback export | all DB slides |
| EN rendered standard slides | `en/slide_N.jpg` | preview, PDF, fallback export | all DB slides when EN translations exist |
| PT rendered HD slides | `pt/hd/slide_N.jpg` | workspace/publish/public preview | all DB slides |
| EN rendered HD slides | `en/hd/slide_N.jpg` | workspace/publish/public preview | all DB slides when EN translations exist |
| PT PDF | `pt/carousel.pdf` | distribution | page count equals DB slide count |
| EN PDF | `en/carousel.pdf` | distribution | page count equals DB slide count when EN translations exist |

`images.slides` in design tokens must not be used to hide incomplete rendered output. If rendered artifacts are incomplete, the workflow should fail, not display four raw images.

## Implementation Plan

### 1. Add A Carousel Artifact Health Service

Create `backend/src/rag_backend/application/services/carousel/artifact_health.py`.

Define typed dataclasses:

```python
@dataclass(frozen=True)
class ImageDimensions:
    width: int
    height: int

@dataclass(frozen=True)
class CarouselArtifactHealthRequest:
    project: CarouselProject
    slides: Sequence[CarouselSlide]
    require_english: bool

@dataclass(frozen=True)
class CarouselArtifactHealthReport:
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    rendered_slide_numbers_pt: tuple[int, ...]
    rendered_slide_numbers_en: tuple[int, ...]
```

Implementation details:

- Derive `expected_slide_numbers` from persisted `CarouselSlide.slide_number`, sorted ascending.
- Derive raw image expected numbers by converting slides to `SlideData` and reusing `filter_image_slides()`.
- Resolve every candidate path under `Path(project.output_dir).resolve()` and reject files outside that directory.
- Validate JPEG files with Pillow:
  - raw AI image files: valid JPEG and above a small byte threshold.
  - standard rendered files: `1080x1350`.
  - HD rendered files: `2160x2700`.
- Validate PDFs with `pypdf.PdfReader`:
  - path exists under the output dir.
  - page count equals expected slide count.
- Return structured errors such as:
  - `missing_output_dir`
  - `missing_raw_image: slide 3`
  - `missing_rendered_pt_hd: slide 7`
  - `invalid_rendered_pt_hd_dimensions: slide 1 is 1080x1080`
  - `missing_pdf_en`
  - `pdf_page_count_mismatch_pt: expected 7 got 4`

Add constants in a dedicated carousel constants module, not inline strings:

- standard render size.
- HD render size.
- language directory names.
- error-code prefixes.
- minimum JPEG byte threshold.

### 2. Wire Artifact Health After Image Approval

Update `backend/src/rag_backend/application/services/carousel/editorial_finalize.py`.

Current behavior:

- `export_and_complete_carousel()` calls `refinement.re_render_slides()`.
- It catches `ValueError`, logs, and returns.
- If render returns, it marks the project completed without artifact validation.

Change:

- Introduce a typed return object:

```python
@dataclass(frozen=True)
class CarouselFinalizeResult:
    completed: bool
    errors: tuple[str, ...]
```

- After `refinement.re_render_slides(UUID(project_id))`, fetch slides from the repository.
- Run `evaluate_carousel_artifacts(CarouselArtifactHealthRequest(...))`.
- Only set `CarouselStatus.COMPLETED` when `report.ok` is true.
- If report fails:
  - keep status non-completed.
  - persist a workflow/project error message.
  - return `CarouselFinalizeResult(completed=False, errors=report.errors)`.
- Update `finalize_carousel_after_images_approval()` to return that result.

Update `backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py`.

Current behavior:

- After images approval, it calls `finalize_carousel_after_images_approval(db, project_id)` and ignores success/failure.

Change:

- Capture the finalize result.
- If `completed=False`, update orchestrator state:
  - `current_phase=PHASE_IMAGES`.
  - `phase_status=PHASE_STATUS_FAILED`.
  - `error_message="Carousel rendered artifacts incomplete: ..."`
  - leave `workflow_status` unchanged.
- Publish a workflow error SSE event.
- Do not allow the run to proceed to final review.

This directly prevents GLM's manual state from being treated as publishable in a clean run.

### 3. Add A Publish-Time Artifact Gate

Update both publish paths so manually mutated DB rows cannot bypass validation.

Files:

- `backend/src/rag_backend/api/routes/carousels/crud.py`
- `backend/src/rag_backend/api/routes/carousels/publishing.py`

Implementation details:

- Before `POST /api/carousels/{id}/publish` sets `is_public=true`, fetch persisted slides and run `evaluate_carousel_artifacts(...)`.
- If unhealthy, return `409 Conflict` with a concise `detail`, for example:
  - `Carousel artifacts incomplete: missing pt/hd slide 7, missing en PDF`
- Before `POST /api/carousels/{id}/publish/instagram`, run the same gate.
- This catches GLM-style status tampering even if `workflow_status=approved_for_publish`.

### 4. Stop Four-Slide Fallbacks In Design Token Helpers

Update `backend/src/rag_backend/api/routes/carousels/helpers.py`.

Current problematic behavior:

- `_build_default_design_tokens()` invents four image URLs when no disk images exist.
- `_apply_draft_preview_urls()` removes `rendered_slides_pt` when `pt/` is missing, then fills `images.slides` from raw images and truncates to four.
- `_has_rendered_slides()` returns true if any slide exists.

Change:

- Introduce a small typed merge context:

```python
@dataclass(frozen=True)
class DesignTokenDiskMergeContext:
    project: CarouselProject
    expected_slide_numbers: tuple[int, ...]
```

- Change `_merge_design_tokens_with_disk(...)` to accept the context or add a wrapper that does.
- Routes that already have `repo` should fetch slides and pass expected numbers.
- If no expected numbers are available, use only disk numbers and do not invent four slide URLs.
- Only set `images.rendered_slides_pt` when PT rendered slide numbers exactly match expected slide numbers.
- Only set `images.rendered_slides_en` when EN rendered slide numbers exactly match expected slide numbers.
- Set `images.slides` to the complete rendered PT list when PT is complete.
- If PT is incomplete, set `images.slides=[]` and keep raw image URLs out of full carousel preview data.
- Keep the single `hero` as the first complete rendered slide when available; otherwise empty string.
- Replace `_has_rendered_slides(output_dir, lang)` with a completeness helper that takes expected slide numbers and optionally requires HD.

Do not implement GLM's suggestion to copy raw images into `pt/` and `en/`. The correct fix is to run `run_bilingual_export()` and validate its output.

### 5. Normalize Output Directory Creation

Update `backend/src/rag_backend/application/services/carousel/editorial_visual_pipeline.py`.

Current behavior:

- `DEFAULT_OUTPUT_BASE = "./output/carousels"`.
- New image generation can persist relative `output_dir` values.

Change:

- Remove the independent `DEFAULT_OUTPUT_BASE`.
- Add `output_base_dir` to `CarouselImageGenerationContext`.
- Build output dir as `Path(output_base_dir) / ctx.project_id`.
- Persist the resolved absolute path in `project.output_dir`.

Update `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py`.

- Add `carousel_output_dir: Path` or string to `PhaseArtifactRunnerDependencies`.
- Pass it into `CarouselImageGenerationContext` in `_ensure_image_artifacts()`.

Update `backend/src/rag_backend/agents/carousel_editorial_orchestrator.py` and DI construction.

- Inject `settings.carousel_output_dir` into `CarouselEditorialOrchestrator`.
- Pass it to `PhaseArtifactRunnerDependencies`.
- Keep constructor argument count compliant by using dataclass config objects where needed.

Update tests that instantiate `PhaseArtifactRunnerDependencies` to pass a temp output root.

### 6. Preserve Provider Failures As Workflow Failures

Update `backend/src/rag_backend/infrastructure/external/openai_image.py`.

Current behavior:

- 403 is translated clearly.
- Other `APIStatusError` values become generic `OpenAI image generation failed`.

Change:

- Add explicit handling for 400 invalid model / invalid value.
- Error text should include provider, configured model, status code, and the vendor message without leaking secrets.
- Preserve the OpenAI error details in a typed error object:
  - status code.
  - provider error type.
  - provider error code.
  - provider error param.
  - provider error message.
  - request model.
  - request size.
  - prompt fingerprint, not the full prompt in exception text.
- The workflow-visible message should be concise; the persisted generation record and logs should carry full details.

Update `backend/src/rag_backend/application/services/carousel/nodes/images.py`.

- When any slide image generation fails, keep `phase_progress.slides[number].status = failed`.
- Return/raise an error that the graph converts into:
  - `phase_status=failed`.
  - `error_message`.
  - no final review transition.
- Do not leave partial raw images as acceptable if the phase failed.

Update `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py`.

- Wrap `generate_carousel_images(...)` in `_ensure_image_artifacts()`.
- On provider failure, return:

```python
{
    "phase_status": PHASE_STATUS_FAILED,
    WORKFLOW_ERROR_KEY: "Image generation failed: ...",
}
```

### 7. Add Image Generation Records, Idempotency, And Recovery

Create a persistent generation record so successful images are reusable and failed images are debuggable.

Recommended data model:

- Add `carousel_image_generations` table.
- Add a domain model and repository protocol for image generation records.
- Use a migration instead of overloading `CarouselSlide.metadata`, because the data is nested, audit-heavy, and needs unique constraints.

Core columns:

| Column | Purpose |
|---|---|
| `id` | Internal UUID for this generation attempt |
| `project_id` | Carousel project UUID |
| `slide_id` | Carousel slide UUID |
| `slide_number` | Query/debug convenience |
| `status` | `pending`, `succeeded`, `failed`, `reused` |
| `provider` | `openai`, `gemini`, etc. |
| `provider_model` | OpenAI image model used |
| `provider_image_id` | Stable provider image ID if the provider returns one |
| `provider_created_at` | OpenAI `created` timestamp when present |
| `provider_revised_prompt` | OpenAI `data[].revised_prompt` when present |
| `generation_key` | Deterministic idempotency key |
| `prompt_hash` | SHA-256 of final prompt |
| `theme_hash` | SHA-256 of theme/style/color payload |
| `content_sha256` | SHA-256 of the stored image bytes |
| `output_path` | Stored image path |
| `request_json` | Sanitized provider request, including model and size |
| `prompt_json` | Raw/editable/final prompt payload |
| `response_json` | Sanitized provider response metadata |
| `error_json` | Structured provider/application error details |
| `started_at`, `completed_at` | Timing and latency analysis |

Important OpenAI detail:

- The currently installed OpenAI SDK image response type exposes `created`, `data[].b64_json`, `data[].url`, and `data[].revised_prompt`.
- It does not expose a stable image ID in this API path.
- Therefore, store `provider_image_id` when any future provider response includes one, but use `generation_key` plus `content_sha256` as the reliable local unique identifiers.

Generation key:

```text
sha256(project_id + slide_id + slide_number + provider + model + size + style + theme_hash + prompt_hash)
```

Use this key before calling OpenAI:

1. Build prompt/theme/style payload.
2. Compute `generation_key`.
3. Look for a succeeded generation with the same key and an existing valid image file.
4. If found, set the slide `image_path` from the existing record and skip the OpenAI call.
5. If found but the file is missing, mark the record stale and regenerate.
6. If no record exists, create a `pending` record, call the provider, then persist success/failure details.

Recovery/backfill:

- Add a maintenance command or script to scan existing `carousel_slides.image_path` files.
- For each valid file:
  - compute `content_sha256`.
  - reconstruct best-effort `prompt_hash` from `CarouselSlide.image_prompt`.
  - compute a best-effort `generation_key` from stored project model/style/theme and prompt.
  - create a `carousel_image_generations` record with `status="recovered"`.
- If no provider ID exists, do not invent one; leave `provider_image_id=NULL`.
- For `72b0641f...`, recovery should mark files as recovered placeholders only if they pass minimum checks. They should still fail artifact health because they are square/no HD/no PDF.

### 8. Expose Editable Image Prompt Details Before Provider Calls

The UI must show the actual prompt package before it is sent to OpenAI, not only a generic `image_prompt`.

Backend changes:

- Extend `backend/src/rag_backend/api/schemas/carousel_workflow.py` `SlideImagePrompt` or add a sibling schema with:
  - slide index and slide type.
  - title/body summary.
  - raw editable prompt.
  - sanitized prompt.
  - provider strategy name.
  - provider model and size.
  - theme name.
  - theme palette colors.
  - style labels.
  - final wrapped provider prompt.
  - prompt hash and generation key.
  - last generation status.
  - last error summary if present.
- Build this prompt package in `backend/src/rag_backend/application/services/carousel/nodes/images.py` or a new `image_prompt_package.py` helper.
- Reuse the same package for:
  - workflow state `slide_image_prompts`.
  - image prompt review UI.
  - image generation request.
  - image generation record persistence.

Frontend changes:

- Update `frontend/src/features/create/components/image-prompt-review.tsx`.
- Show prompt details in an editable form before images phase approval:
  - raw prompt textarea.
  - final prompt preview, read-only unless advanced mode is enabled.
  - theme/color chips.
  - provider/model/size.
  - generation key.
  - prior image thumbnail when a reusable image exists.
  - last error details.
- Allow reviewer edits to be submitted as structured feedback for the images phase.
- Persist edited prompts back to slides before calling the provider.
- If an existing generation key matches, show "Image can be reused" and skip provider generation unless reviewer forces regeneration.

### 9. Add Full Image Generation Error Visibility

Errors need to be visible in logs, workflow state, API responses, and UI.

Logging requirements:

- Add structured logs around each slide image generation attempt:
  - `image_generation_started`
  - `image_generation_reused`
  - `image_generation_succeeded`
  - `image_generation_failed`
- Every log must include:
  - `project_id`.
  - `slide_id`.
  - `slide_number`.
  - `provider`.
  - `provider_model`.
  - `image_style`.
  - `generation_key`.
  - `prompt_hash`.
  - `output_path`.
  - `duration_ms`.
  - OpenAI `status_code`, `error.type`, `error.code`, `error.param`, and `error.message` when available.
- Do not log API keys.
- Log prompt hashes by default; store full prompts in the generation record and workflow state where the authenticated UI can display/edit them.

Workflow/API visibility:

- Add `image_generation_errors` to workflow state or include errors in `phase_progress.slides`.
- Include:
  - slide number.
  - provider/model.
  - human-readable summary.
  - provider error details.
  - retryable boolean.
  - generation key.
- `WorkflowFailedCard` should show the image phase error summary and link back to image prompt review.

Recovery behavior:

- If image generation fails because of provider/model configuration, keep prompts and generated keys so the user can switch provider/model and retry.
- If image generation fails for one slide, do not discard successful records for other slides.
- On retry, reuse succeeded records with unchanged generation keys and only call OpenAI for missing/changed/failed slides.

### 10. Fix Public And Instagram Image URL Builders

Update `backend/src/rag_backend/api/routes/carousels/helpers.py`.

Current behavior:

- `_build_public_image_urls(project_id, slides_count=4)` hardcodes four raw image URLs.

Change:

- Replace it with a project-aware function:

```python
@dataclass(frozen=True)
class PublicImageUrlRequest:
    project: CarouselProject
    slide_numbers: tuple[int, ...]
    language: str
```

- Return rendered slide URLs, not raw `images/` URLs.
- Default Instagram language should be explicit, likely PT unless UI passes EN.
- Use all expected slide numbers.
- Remove the default `slides_count=4`.

Update `backend/src/rag_backend/api/routes/carousels/publishing.py`.

- Fetch project and slides before building URLs.
- Run artifact health gate.
- Build public URLs from rendered artifacts.

### 11. Update Frontend To Treat Rendered Slides As Required

Update `frontend/src/app/dashboard/create/workspace/create-carousel-preview.tsx`.

Current behavior:

- `extractRenderedSlides()` falls back to `images.slides` and can show four raw images.

Change:

- Prefer `rendered_slides_pt` or `rendered_slides_en`.
- Treat `images.slides` as usable only if its length matches the expected rendered count from the design response or project metadata.
- If rendered slides are absent/incomplete, show an explicit broken-artifact state instead of silently rendering a shorter carousel.

Update `frontend/src/features/publish/components/publish-panel.tsx`.

- Remove or restrict fallback from `rendered_slides_pt` to `images.slides`.
- If rendered slides are missing, show "Rendered slides are incomplete" and disable Instagram publish controls.

Update `frontend/src/lib/carousel-media-url.ts`.

- Ensure rendered slide paths map to `/preview/images/slide_N.jpg?lang=...` for drafts and public rendered slide routes for published content.

### 12. Test Plan

Backend Gherkin scenarios to add:

- `backend/tests/features/carousel_artifact_health.feature`
  - Scenario: 7-slide carousel with complete PT/EN standard, HD, and PDFs passes artifact health.
  - Scenario: square placeholder rendered slide fails artifact health.
  - Scenario: missing PT HD slide blocks final approval.
  - Scenario: CTA has no raw image but complete rendered slides pass.
  - Scenario: missing raw content-slide image fails image phase health.
  - Scenario: 4 hardcoded public image URLs are never returned for a 7-slide carousel.
  - Scenario: unchanged image prompt/theme/model reuses an existing generation record.
  - Scenario: changed image prompt computes a new generation key and regenerates only that slide.
  - Scenario: OpenAI invalid-model error is visible in workflow state and structured logs.
  - Scenario: reviewer edits image prompt details before the provider call.

Backend unit tests:

- New `backend/tests/unit/application/test_carousel_artifact_health.py`.
- Update `backend/tests/unit/application/test_editorial_finalize.py`:
  - render success plus healthy artifacts marks completed.
  - render success plus missing HD returns failed finalize result and does not mark completed.
- Update `backend/tests/unit/application/test_phase_artifact_runner.py`:
  - provider failure in `_ensure_image_artifacts()` returns `PHASE_STATUS_FAILED`.
  - output root is passed to `generate_carousel_images`.
- Update `backend/tests/unit/api/test_helpers.py`:
  - no expected slides means no invented four image URLs.
  - incomplete PT/EN rendered dirs do not populate rendered fields.
  - complete 7 rendered slides populate all 7 URLs.
  - `images.slides` is not truncated to 4 for complete rendered output.
- Update `backend/tests/unit/api/test_publish*.py` or add route tests:
  - site publish returns 409 when artifact health fails.
  - Instagram publish returns 409 when artifact health fails.
  - Instagram publish uses all rendered slide URLs.
- Update `backend/tests/unit/infrastructure/test_openai_image_service.py`:
  - 400 invalid model maps to a clear RuntimeError.
- Add tests for the new generation record service:
  - successful provider call persists generation metadata.
  - provider response without image ID still stores generation key and content hash.
  - existing generation key skips provider call.
  - missing file for existing generation key triggers regeneration.
  - provider error persists `error_json`.
- Add tests for prompt package builder:
  - final prompt includes theme name, palette colors, style label, and provider strategy wrapper.
  - prompt package exposes editable and final prompts separately.

Frontend tests:

- Update `frontend/src/app/dashboard/create/workspace/create-carousel-preview` tests or add one:
  - incomplete rendered slides show an error state, not a four-slide carousel.
- Update `frontend/src/features/publish/components/publish-panel.test.tsx`:
  - missing rendered slides disables publishing.
  - seven rendered PT/EN slides render seven viewer slides.
- Update `frontend/src/lib/carousel-media-url` tests:
  - rendered preview URLs keep language query and cache buster.
- Update `frontend/src/features/create/components/image-prompt-review.test.tsx`:
  - renders theme/color/model/final prompt details.
  - allows raw prompt edits.
  - displays generation key and prior error details.

Manual / smoke:

- Run `scripts/carousel_visual_qa.py` for the regenerated target project.
- Verify both PT and EN contact sheets.
- Confirm `GET /api/carousels/{id}` returns 7 `rendered_slides_pt` and 7 `rendered_slides_en`.
- Confirm `POST /publish` rejects `72b0641f...` until HD and PDFs exist.
- Trigger an image provider failure in a controlled test configuration and verify:
  - logs include provider error details.
  - UI shows what happened.
  - retry reuses already successful image generations.

### 13. Rollout And Recovery

1. Reset the admin password to the expected value.
2. Mark `72b0641f-17f7-4d49-8906-92c6fedaeaba` as a failed/manual artifact or delete/recreate it after backup.
3. Do not use `72b0641f...` as visual baseline.
4. Keep `191223a4-9499-4e66-84d6-e78bdee4e695` as current known-good verification input because visual QA passes.
5. Implement artifact health first, before rerunning generation.
6. Backfill/recover image generation records from valid existing `image_path` files.
7. Re-run generation from a clean workflow state only after final/publish gates reject incomplete artifacts.

## Acceptance Criteria

- A carousel with DB 7 slides cannot expose only four preview/publish slides.
- `approved_for_publish` cannot be reached if rendered PT/EN slides, HD slides, or PDFs are incomplete.
- Manual DB status changes cannot bypass publish artifact validation.
- Raw AI images are not copied into `pt/` or `en/` as a substitute for rendered exports.
- Instagram publish uses rendered carousel slides and all expected slide numbers.
- Output directories are absolute and rooted under configured `carousel_output_dir`.
- Provider/model failures produce clear workflow errors and do not become placeholder images.
- `scripts/carousel_visual_qa.py` passes for the clean regenerated target carousel.
