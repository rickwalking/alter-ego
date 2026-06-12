# Workflow Resume Failure: Missing Images Investigation

**Date:** 2026-06-05
**Carousel ID:** `ebdf5f04-dbf2-487e-bd88-54e6cd4bf366`
**Ticket/PR:** https://github.com/rickwalking/alter-ego/pull/11

## Symptoms

- Content generated successfully (outline, slide drafts, caption, blog, LinkedIn posts)
- All preview images return `404 Not Found`
- No error feedback shown to the user in the UI
- Images directory on disk is empty

## Investigation

### DB State

```sql
current_phase: images
phase_status:  failed
status:         pending
image_model:   openai
image_style:   neo_anime
output_dir:    output/carousels/ebdf5f04-dbf2-487e-bd88-54e6cd4bf366
```

All 7 slides exist in `carousel_slides` but `image_path` is `NULL` for every slide.

### File System

```
/app/output/carousels/ebdf5f04-dbf2-487e-bd88-54e6cd4bf366/images/
  → empty (only . and ..)
```

No image files were ever written to disk.

### Logs

```
2026-06-05T15:35:18.724494Z [error] background_resume_failed project_id=ebdf5f04-dbf2-487e-bd88-54e6cd4bf366
```

Checkpoint data reveals `workflow_error: "Invalid JSON response from LLM"` carried over from the content phase (step 50057). The crash occurred at step 50058/50059 during the **design phase** execution.

## Root Cause

The `background_resume_failed` error in `editorial_workflow_resume_runner.py:92-103`:

```python
except Exception:
    await db.rollback()
    logger.exception("background_resume_failed", project_id=params.project_id)
    await _mark_background_resume_failed(
        service, params.project_id, ERR_BACKGROUND_RESUME_FAILED, recoverable=True,
    )
```

Catches **all exceptions** during workflow resume but only logs the error — it is never surfaced to the user via API or SSE.

### Primary Bug: Missing `PHASE_STATUS_FAILED` Guards

In `carousel_workflow_nodes.py`, `content_phase_async` properly guards against artifact generation failure:

```python
async def content_phase_async(state, config):
    merged = dict(state)
    merged.update(await ensure_artifacts(state, config, PHASE_CONTENT))
    if merged.get("phase_status") == PHASE_STATUS_FAILED:   # ← This guard exists
        return merged
    sync_result = content_phase(cast(CarouselWorkflowState, merged), config)
    return {**merged, **sync_result}
```

But both `design_phase_async` and `images_phase_async` are **missing this guard**:

```python
async def design_phase_async(state, config):
    merged = dict(state)
    merged.update(await ensure_artifacts(state, config, PHASE_DESIGN))
    # ← NO GUARD — if ensure_artifacts fails internally, exception propagates
    sync_result = design_phase(cast(CarouselWorkflowState, merged), config)
    return {**merged, **sync_result}

async def images_phase_async(state, config):
    merged = dict(state)
    merged.update(await ensure_artifacts(state, config, PHASE_IMAGES))
    # ← NO GUARD — same vulnerability
    sync_result = images_phase(cast(CarouselWorkflowState, merged), config)
    return {**merged, **sync_result}
```

When `_ensure_design_artifacts` throws (e.g., due to `run_design()` failure), the exception propagates unhandled through:
1. `design_phase_async` → LangGraph → `service.resume_workflow()` → `_execute_background_resume()`
2. Caught by the blanket `except Exception:` in the background resume runner
3. Project marked as `failed` — no user feedback

### Secondary: No User-Facing Error Propagation

The `_mark_background_resume_failed` function only persists the error to DB and emits an SSE event, but the frontend never displays it. The user sees an infinite loading state or missing images with no explanation.

## Proposed Fix

### Fix 1: Add `PHASE_STATUS_FAILED` guard to `design_phase_async`

File: `backend/src/rag_backend/agents/carousel_workflow_nodes.py`

```python
async def design_phase_async(
    state: CarouselWorkflowState,
    config: RunnableConfig,
) -> dict[str, object]:
    merged = dict(state)
    merged.update(await ensure_artifacts(state, config, PHASE_DESIGN))
    if merged.get("phase_status") == PHASE_STATUS_FAILED:
        return merged
    sync_result = design_phase(cast(CarouselWorkflowState, merged), config)
    return {**merged, **sync_result}
```

### Fix 2: Add `PHASE_STATUS_FAILED` guard to `images_phase_async`

```python
async def images_phase_async(
    state: CarouselWorkflowState,
    config: RunnableConfig,
) -> dict[str, object]:
    merged = dict(state)
    merged.update(await ensure_artifacts(state, config, PHASE_IMAGES))
    if merged.get("phase_status") == PHASE_STATUS_FAILED:
        return merged
    sync_result = images_phase(cast(CarouselWorkflowState, merged), config)
    return {**merged, **sync_result}
```

### Fix 3: Add error handling to `_ensure_design_artifacts`

File: `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py`

Wrap `apply_design_tokens` in a try/except so that an exception sets `phase_status` to `PHASE_STATUS_FAILED` instead of propagating:

```python
async def _ensure_design_artifacts(self, state, pending):
    if self._db is None:
        return {}
    outline = pending.get("outline") or state.get("outline") or []
    if not isinstance(outline, list):
        return {}
    slides = await ensure_slides_from_outline(
        self._db,
        str(state.get("project_id", "")),
        [slide for slide in outline if isinstance(slide, dict)],
    )
    if not slides:
        return {}
    try:
        await apply_design_tokens(
            self._db,
            str(state.get("project_id", "")),
            slides,
        )
    except Exception:
        return {
            "phase_status": PHASE_STATUS_FAILED,
            WORKFLOW_ERROR_KEY: "Design token application failed",
        }
    return {"design_applied": True}
```

### Fix 4: Surface background resume errors to the user

The `_mark_background_resume_failed` already emits SSE error events. The frontend should subscribe to these events and display a toast/banner when `workflow_error` is present in the project state.

## Files Changed

| File | Change |
|------|--------|
| `backend/src/rag_backend/agents/carousel_workflow_nodes.py` | Add `PHASE_STATUS_FAILED` guard to `design_phase_async` and `images_phase_async` |
| `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py` | Wrap `apply_design_tokens` in try/except in `_ensure_design_artifacts` |
| `frontend/` (to be determined) | Subscribe to SSE error events and display to user |
