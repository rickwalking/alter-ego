#!/usr/bin/env python3
"""Repair editorial workflow slides when draft_text contains stringified bilingual dicts."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import cast

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from rag_backend.agents.carousel_workflow_engine import CarouselWorkflowEngine
from rag_backend.application.services.carousel.malformed_draft_builders import (
    _BODY_FIELD,
    _DRAFT_TEXT_FIELD,
    _HEADING_FIELD,
    _IMAGE_PROMPT_FIELD,
    _LANG_EN_KEY,
    _LANG_PT_KEY,
    _POLICY_VERSION_FIELD,
    _PRESENTATION_EN_FIELD,
    _PRESENTATION_PT_FIELD,
    _SLIDE_INDEX_FIELD,
    _SLIDE_TYPE_FIELD,
    _TITLE_FIELD,
    _TLDR_STRIP_FIELD,
    _as_mapping,
    _parse_draft_blob,
    build_locale_presentation,
    polish_repaired_slides,
)
from rag_backend.application.services.carousel.malformed_draft_normalizer import (
    normalize_slide_drafts,
)
from rag_backend.application.services.carousel.presentation_review import (
    build_presentation_review_updates,
    serialize_translations_en,
)
from rag_backend.domain.constants.carousel import (
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_INTRO,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_AWAITING_HUMAN
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.infrastructure.config.settings import get_settings

# Workflow state key constants
_STATE_SLIDE_DRAFTS = "slide_drafts"
_STATE_CURRENT_PHASE = "current_phase"
_REVIEW_PRESENTATION_VALIDATION = "presentation_validation"
_REVIEW_PRESENTATION_POLICY_VERSION = "presentation_policy_version"
_REVIEW_TRANSLATIONS_EN = "translations_en"
_REVIEW_PHASE_STATUS = "phase_status"
_RESULT_PROJECT_ID = "project_id"
_RESULT_SLIDE_COUNT = "slide_count"
_RESULT_BLOCKING = "blocking"
_RESULT_VIOLATION_COUNT = "violation_count"
_RESULT_POLICY_VERSION = "policy_version"
_RESULT_VALIDATION = "validation"
_VALIDATION_BLOCKING = "blocking"
_VALIDATION_VIOLATIONS = "violations"
_DEFAULT_AS_NODE = "content"


def repair_slide_drafts(slide_drafts: list[dict[str, object]]) -> list[dict[str, object]]:  # noqa: PLR0914
    """Normalize malformed draft_text blobs into presentation_pt/en payloads."""
    repaired: list[dict[str, object]] = []
    for slide in slide_drafts:
        if not isinstance(slide, dict):
            continue
        slide_type = str(slide.get(_SLIDE_TYPE_FIELD) or SLIDE_TYPE_CONTENT)
        slide_index = int(slide.get(_SLIDE_INDEX_FIELD) or len(repaired) + 1)
        parsed = _parse_draft_blob(slide.get(_DRAFT_TEXT_FIELD))
        if parsed is None:
            repaired.append(dict(slide))
            continue

        pt_data = _as_mapping(parsed.get(_LANG_PT_KEY)) or {}
        en_data = _as_mapping(parsed.get(_LANG_EN_KEY)) or {}
        tldr_strip = slide.get(_TLDR_STRIP_FIELD)
        tldr_value = str(tldr_strip).strip() if isinstance(tldr_strip, str) and tldr_strip.strip() else None
        image_prompt = parsed.get(_IMAGE_PROMPT_FIELD)
        if not isinstance(image_prompt, str):
            image_prompt = pt_data.get(_IMAGE_PROMPT_FIELD) or en_data.get(_IMAGE_PROMPT_FIELD)
        image_prompt_value = str(image_prompt).strip() if isinstance(image_prompt, str) and image_prompt.strip() else None

        presentation_pt = build_locale_presentation(
            slide_type,
            pt_data,
            tldr_strip=tldr_value if slide_type == SLIDE_TYPE_INTRO else None,
            icon_offset=0,
        )
        presentation_en = build_locale_presentation(
            slide_type,
            en_data,
            icon_offset=0,
        )

        updated = dict(slide)
        updated.update({
            _SLIDE_INDEX_FIELD: slide_index,
            _SLIDE_TYPE_FIELD: slide_type,
            _TITLE_FIELD: presentation_pt.get(_HEADING_FIELD, ""),
            _PRESENTATION_PT_FIELD: presentation_pt,
            _PRESENTATION_EN_FIELD: presentation_en,
            _DRAFT_TEXT_FIELD: str(presentation_pt.get(_BODY_FIELD) or ""),
            _POLICY_VERSION_FIELD: str(slide.get(_POLICY_VERSION_FIELD) or DEFAULT_PRESENTATION_POLICY_VERSION),
        })
        if image_prompt_value:
            updated[_IMAGE_PROMPT_FIELD] = image_prompt_value
        repaired.append(updated)
    polish_repaired_slides(repaired)
    return repaired


def _translations_from_slides(slides: list[dict[str, object]]) -> dict[int, dict[str, object]]:
    """Extract English translations from repaired slide presentations."""
    translations: dict[int, dict[str, object]] = {}
    for slide in slides:
        slide_index = int(slide.get(_SLIDE_INDEX_FIELD) or 0)
        presentation_en = _as_mapping(slide.get(_PRESENTATION_EN_FIELD))
        if slide_index <= 0 or presentation_en is None:
            continue
        translations[slide_index] = {
            _HEADING_FIELD: str(presentation_en.get(_HEADING_FIELD) or ""),
            _BODY_FIELD: str(presentation_en.get(_BODY_FIELD) or ""),
        }
    return translations


async def repair_workflow(project_id: str, *, dry_run: bool = False) -> dict[str, object]:  # noqa: PLR0914
    """Load workflow state, repair slide drafts, and update state."""
    settings = get_settings()
    async with AsyncSqliteSaver.from_conn_string(settings.carousel_checkpoint_sqlite_path) as checkpointer:
        engine = CarouselWorkflowEngine(checkpointer=checkpointer)
        state = await engine.get_state(project_id)
        if state is None:
            raise RuntimeError(f"No workflow state found for project {project_id}")

        raw_drafts = state.get(_STATE_SLIDE_DRAFTS)
        if not isinstance(raw_drafts, list):
            msg = "Workflow state has no slide_drafts to repair"
            raise TypeError(msg)

        draft_dicts = [slide for slide in raw_drafts if isinstance(slide, dict)]
        repaired_drafts = normalize_slide_drafts(draft_dicts)
        polish_repaired_slides(repaired_drafts)
        translations_en = _translations_from_slides(repaired_drafts)
        review_updates = build_presentation_review_updates(
            repaired_drafts,
            translations_en=translations_en,
            policy_version=DEFAULT_PRESENTATION_POLICY_VERSION,
        )

        validation = review_updates.get(_REVIEW_PRESENTATION_VALIDATION)
        blocking = False
        violation_count = 0
        if isinstance(validation, dict):
            blocking = validation.get(_VALIDATION_BLOCKING) is True
            violations = validation.get(_VALIDATION_VIOLATIONS)
            violation_count = len(violations) if isinstance(violations, list) else 0

        result = {
            _RESULT_PROJECT_ID: project_id,
            _RESULT_SLIDE_COUNT: len(repaired_drafts),
            _RESULT_BLOCKING: blocking,
            _RESULT_VIOLATION_COUNT: violation_count,
            _RESULT_POLICY_VERSION: review_updates.get(_REVIEW_PRESENTATION_POLICY_VERSION),
        }

        if dry_run:
            result[_RESULT_VALIDATION] = validation
            return result

        updates: dict[str, object] = {
            _STATE_SLIDE_DRAFTS: repaired_drafts,
            **review_updates,
            _REVIEW_TRANSLATIONS_EN: serialize_translations_en(translations_en),
            _REVIEW_PRESENTATION_POLICY_VERSION: DEFAULT_PRESENTATION_POLICY_VERSION,
            _REVIEW_PHASE_STATUS: PHASE_STATUS_AWAITING_HUMAN,
        }
        as_node = str(state.get(_STATE_CURRENT_PHASE) or _DEFAULT_AS_NODE)
        await engine.update_state(project_id, updates, as_node=as_node)
        return result


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Entry point for the repair workflow script."""
    args = _parse_args()
    result = asyncio.run(repair_workflow(str(args.project_id), dry_run=bool(args.dry_run)))
    print(json.dumps(result, indent=2))
    if cast(bool, result.get(_RESULT_BLOCKING)):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
