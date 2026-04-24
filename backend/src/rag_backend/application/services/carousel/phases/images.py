"""Phase 5: parallel image generation with Send fan-out.

Each slide needing an image becomes its own graph task via LangGraph
``Send``. Per-item checkpointing means a resumed graph only re-runs the
slides that didn't complete.

Closure-scoped mutable state (progress lock + status boxes) is isolated
inside ``build_image_nodes`` so each graph compilation gets a fresh,
isolated tracker.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict

from langgraph.types import Send

from rag_backend.application.services.carousel.nodes.images import (
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_IN_FLIGHT,
    build_initial_status,
    filter_image_slides,
    run_image_one,
    style_display_name,
)
from rag_backend.application.services.carousel.phases.constants import (
    NODE_IMAGE_WORKER,
)
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.application.services.carousel.types import SlideData, unpack_extras
from rag_backend.domain.models import CarouselProject, CarouselStatus

NODE_IMAGES_DISPATCH = "images_dispatch"
NODE_IMAGES_COLLECT = "images_collect"

_ERR_IMAGE_GENERATION_FAILED = "image generation failed for slides: {}"


class _ImageWorkerState(TypedDict):
    """Per-slide payload for the image fan-out workers."""

    slide: SlideData
    output_dir: str
    worker_index: int
    project: CarouselProject
    all_slides: list[SlideData]


@dataclass
class _ImagePhaseState:
    """Mutable shared state for the image phase closure."""

    progress_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    slide_status_box: list[list[dict[str, str | int]]] = field(default_factory=lambda: [[]])
    style_label_box: list[str] = field(default_factory=lambda: [""])
    total_box: list[int] = field(default_factory=lambda: [0])


async def _publish_progress(
    project: CarouselProject,
    *,
    deps: object,
    phase_state: _ImagePhaseState,
) -> CarouselProject:
    """Read-modify-write on ``project.phase_progress`` under a lock."""
    async with phase_state.progress_lock:
        project.phase_progress = {
            "phase": project.status.value,
            "label": (
                f"Generating {phase_state.total_box[0]} slide images in parallel"
                f" — {phase_state.style_label_box[0]}"
            ),
            "current": sum(
                1 for s in phase_state.slide_status_box[0] if s["status"] == STATUS_DONE
            ),
            "total": phase_state.total_box[0],
            "slides": [dict(s) for s in phase_state.slide_status_box[0]],
        }
        return await deps.repo.update_project(project)


async def _images_dispatch_node(
    state: PipelineState,
    *,
    deps: object,
    phase_state: _ImagePhaseState,
) -> dict[str, object]:
    """Publish initial per-slide pending snapshot and transition status."""
    project: CarouselProject = state["project"]
    project.update_status(CarouselStatus.GENERATING_IMAGES)
    project = await deps.repo.update_project(project)

    slides_with_images = filter_image_slides(state["slides_data"])
    style_label = style_display_name(project.image_model, project.image_style)
    phase_state.style_label_box[0] = style_label
    phase_state.total_box[0] = len(slides_with_images)
    phase_state.slide_status_box[0] = build_initial_status(slides_with_images, style_label)

    project = await _publish_progress(project, deps=deps, phase_state=phase_state)
    return {"project": project}


def _dispatch_image_sends(
    state: PipelineState,
) -> list[Send]:
    """Return one Send per slide needing an image (empty list = skip)."""
    project: CarouselProject = state["project"]
    slides_with_images = filter_image_slides(state["slides_data"])
    return [
        Send(
            NODE_IMAGE_WORKER,
            _ImageWorkerState(
                slide=sd,
                output_dir=state["output_dir"],
                worker_index=i,
                project=project,
                all_slides=slides_with_images,
            ),
        )
        for i, sd in enumerate(slides_with_images)
    ]


async def _image_worker_node(
    worker_state: _ImageWorkerState,
    *,
    deps: object,
    phase_state: _ImagePhaseState,
) -> dict[str, object]:
    """Generate one slide image. Writes ``image_results`` via reducer.

    Idempotency: if the target JPG already exists on disk, skip the
    API call. A resumed graph only pays for slides still in-flight.
    """
    slide = worker_state["slide"]
    index = worker_state["worker_index"]
    output_dir = Path(worker_state["output_dir"])
    project = worker_state["project"]
    image_path = str(output_dir / "images" / f"slide_{slide.slide_number}.jpg")

    # On resume the shared progress list is empty. Rebuild it from
    # the worker payload so indexing works below.
    if not phase_state.slide_status_box[0]:
        style_label = style_display_name(project.image_model, project.image_style)
        phase_state.style_label_box[0] = style_label
        all_slides = worker_state.get("all_slides")
        if all_slides is None:
            db_slides = await deps.repo.get_slides_by_project(project.id)
            all_slides = filter_image_slides([unpack_extras(s) for s in db_slides])
        phase_state.total_box[0] = len(all_slides)
        phase_state.slide_status_box[0] = build_initial_status(all_slides, style_label)

    if Path(image_path).exists():
        phase_state.slide_status_box[0][index]["status"] = STATUS_DONE
        return {
            "image_results": [
                {
                    "number": slide.slide_number,
                    "status": STATUS_DONE,
                    "path": image_path,
                    "skipped": True,
                }
            ]
        }

    phase_state.slide_status_box[0][index]["status"] = STATUS_IN_FLIGHT
    await _publish_progress(project, deps=deps, phase_state=phase_state)

    try:
        generated_path = await run_image_one(
            project, slide, output_dir, image_registry=deps.image_registry
        )
    except Exception:
        phase_state.slide_status_box[0][index]["status"] = STATUS_FAILED
        await _publish_progress(project, deps=deps, phase_state=phase_state)
        raise

    phase_state.slide_status_box[0][index]["status"] = STATUS_DONE
    await _publish_progress(project, deps=deps, phase_state=phase_state)
    return {
        "image_results": [
            {
                "number": slide.slide_number,
                "status": STATUS_DONE,
                "path": generated_path,
            }
        ]
    }


async def _images_collect_node(state: PipelineState) -> dict[str, object]:
    """Fan-in: after all workers finish, surface any failures."""
    results = state.get("image_results", [])
    failed = [r for r in results if r.get("status") == STATUS_FAILED]
    if failed:
        raise RuntimeError(_ERR_IMAGE_GENERATION_FAILED.format([r["number"] for r in failed]))
    return {"project": state["project"]}


def build_image_nodes(deps: object) -> tuple[object, object, object, object]:
    """Return (dispatch_node, worker_node, collect_node, dispatch_sends).

    The returned functions are closure-bound to a fresh
    ``asyncio.Lock`` and mutable progress boxes, so concurrent
    ``Send`` workers update a shared tracker without cross-run bleed.
    """
    phase_state = _ImagePhaseState()

    async def dispatch_node(state: PipelineState) -> dict[str, object]:
        return await _images_dispatch_node(state, deps=deps, phase_state=phase_state)

    async def worker_node(worker_state: _ImageWorkerState) -> dict[str, object]:
        return await _image_worker_node(worker_state, deps=deps, phase_state=phase_state)

    def dispatch_sends(state: PipelineState) -> list[Send]:
        return _dispatch_image_sends(state)

    async def collect_node(state: PipelineState) -> dict[str, object]:
        return await _images_collect_node(state)

    return dispatch_node, worker_node, collect_node, dispatch_sends
