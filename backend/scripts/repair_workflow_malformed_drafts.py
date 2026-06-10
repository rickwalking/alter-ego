#!/usr/bin/env python3
"""Repair editorial workflow slides when draft_text contains stringified bilingual dicts."""

from __future__ import annotations

import argparse
import ast
import asyncio
import json
from collections.abc import Mapping
from typing import cast

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from rag_backend.agents.carousel_workflow_engine import CarouselWorkflowEngine
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
)
from rag_backend.application.services.carousel.malformed_draft_normalizer import (
    normalize_slide_drafts,
)
from rag_backend.application.services.carousel.presentation_review import (
    build_presentation_review_updates,
    serialize_translations_en,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_AWAITING_HUMAN
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.infrastructure.config.settings import get_settings

SUMMARY_ICONS = ("brain", "target", "shield-check")
ACTION_ICONS = ("target", "flask-conical", "brain", "shield-check")


def _as_mapping(value: object) -> dict[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _parse_draft_blob(raw: object) -> dict[str, object] | None:
    if isinstance(raw, dict):
        return dict(raw)
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return None
    return dict(parsed) if isinstance(parsed, dict) else None


def _feature_item(item: Mapping[str, object], *, default_icon: str) -> dict[str, str]:
    icon = item.get("icon_name")
    return {
        "icon_name": str(icon).strip() if isinstance(icon, str) and icon.strip() else default_icon,
        "title": str(item.get("title") or ""),
        "body": str(item.get("body") or ""),
    }


def _build_locale_presentation(
    slide_type: str,
    locale_data: Mapping[str, object],
    *,
    tldr_strip: str | None = None,
    icon_offset: int = 0,
) -> dict[str, object]:
    if slide_type == "intro":
        payload: dict[str, object] = {
            "slide_type": "intro",
            "heading": str(locale_data.get("heading") or ""),
            "body": str(locale_data.get("subtitle") or locale_data.get("body") or ""),
        }
        if tldr_strip:
            payload["tldr_strip"] = tldr_strip
        return payload

    if slide_type == "summary":
        raw_points = locale_data.get("points") or locale_data.get("summary_points") or []
        points = [item for item in raw_points if isinstance(item, Mapping)] if isinstance(raw_points, list) else []
        return {
            "slide_type": "summary",
            "heading": str(locale_data.get("heading") or ""),
            "body": "",
            "summary_points": [
                _feature_item(point, default_icon=SUMMARY_ICONS[(icon_offset + index) % len(SUMMARY_ICONS)])
                for index, point in enumerate(points[:3])
            ],
        }

    if slide_type == "content":
        raw_features = locale_data.get("features") or []
        features = [item for item in raw_features if isinstance(item, Mapping)] if isinstance(raw_features, list) else []
        return {
            "slide_type": "content",
            "heading": str(locale_data.get("heading") or ""),
            "body": str(locale_data.get("body") or ""),
            "content_kind": "features",
            "features": [
                _feature_item(feature, default_icon=SUMMARY_ICONS[(icon_offset + index) % len(SUMMARY_ICONS)])
                for index, feature in enumerate(features[:3])
            ],
        }

    if slide_type == "closing":
        raw_actions = locale_data.get("actions") or locale_data.get("features") or []
        actions = [item for item in raw_actions if isinstance(item, Mapping)] if isinstance(raw_actions, list) else []
        return {
            "slide_type": "closing",
            "heading": str(locale_data.get("heading") or ""),
            "body": str(locale_data.get("body") or ""),
            "actions": [
                _feature_item(action, default_icon=ACTION_ICONS[(icon_offset + index) % len(ACTION_ICONS)])
                for index, action in enumerate(actions[:4])
            ],
        }

    return {
        "slide_type": "cta",
        "heading": str(locale_data.get("title") or locale_data.get("heading") or ""),
        "body": str(locale_data.get("body") or ""),
        "creator_name": str(
            locale_data.get("cta_creator_name") or locale_data.get("creator_name") or ""
        ),
        "creator_handle": str(
            locale_data.get("cta_handle") or locale_data.get("creator_handle") or ""
        ),
        "creator_website": str(
            locale_data.get("cta_website") or locale_data.get("creator_website") or ""
        ),
    }


def _truncate_visible_copy(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return truncated.rstrip(" ,.;:")


def _polish_repaired_slides(slides: list[dict[str, object]]) -> None:
    """Apply deterministic copy fixes for known budget and parity issues."""
    for slide in slides:
        slide_index = int(slide.get("slide_index") or 0)
        presentation_pt = _as_mapping(slide.get(PRESENTATION_PT_KEY))
        presentation_en = _as_mapping(slide.get(PRESENTATION_EN_KEY))
        if presentation_pt is None or presentation_en is None:
            continue

        if slide_index == 1:
            tldr_pt = presentation_pt.get("tldr_strip")
            if isinstance(tldr_pt, str) and tldr_pt.strip():
                presentation_en["tldr_strip"] = (
                    "Fable 5 and Mythos 5 are here. Glassglowing changes cybersecurity."
                )

        if slide_index == 3:
            presentation_pt["body"] = (
                "Ambos os modelos compartilham a mesma família na Anthropic, com "
                "<strong>capacidades avançadas e controle de riscos</strong> desde a base."
            )
            presentation_en["body"] = (
                "Both models share the same Anthropic family, with "
                "<strong>advanced capabilities and built-in risk control</strong> from day one."
            )

        if slide_index == 4:
            presentation_pt["body"] = _truncate_visible_copy(
                "O Claude Mythos 5 supera modelos existentes em segurança ofensiva e "
                "defensiva. Especialistas o tratam como <strong>referência no setor</strong> "
                "após avaliação de risco rigorosa.",
                220,
            )
            presentation_en["body"] = _truncate_visible_copy(
                "Claude Mythos 5 outperforms existing models in offensive and defensive "
                "security. Experts now treat it as the <strong>industry benchmark</strong> "
                "after rigorous risk review.",
                220,
            )

        if slide_index == 5:
            presentation_pt["body"] = _truncate_visible_copy(
                "Diferente do Mythos 5, o Fable 5 passou por salvaguardas estruturadas "
                "antes do lançamento. Riscos iniciais foram eliminados para entregar "
                "<strong>capacidades avançadas com segurança</strong>.",
                220,
            )

        slide[PRESENTATION_PT_KEY] = presentation_pt
        slide[PRESENTATION_EN_KEY] = presentation_en
        if slide_index in {3, 4, 5}:
            slide["draft_text"] = str(presentation_pt.get("body") or "")


def repair_slide_drafts(slide_drafts: list[dict[str, object]]) -> list[dict[str, object]]:
    """Normalize malformed draft_text blobs into presentation_pt/en payloads."""
    repaired: list[dict[str, object]] = []
    for slide in slide_drafts:
        if not isinstance(slide, dict):
            continue
        slide_type = str(slide.get("slide_type") or "content")
        slide_index = int(slide.get("slide_index") or len(repaired) + 1)
        parsed = _parse_draft_blob(slide.get("draft_text"))
        if parsed is None:
            repaired.append(dict(slide))
            continue

        pt_data = _as_mapping(parsed.get("pt")) or {}
        en_data = _as_mapping(parsed.get("en")) or {}
        tldr_strip = slide.get("tldr_strip")
        tldr_value = str(tldr_strip).strip() if isinstance(tldr_strip, str) and tldr_strip.strip() else None
        image_prompt = parsed.get("image_prompt")
        if not isinstance(image_prompt, str):
            image_prompt = pt_data.get("image_prompt") or en_data.get("image_prompt")
        image_prompt_value = str(image_prompt).strip() if isinstance(image_prompt, str) and image_prompt.strip() else None

        presentation_pt = _build_locale_presentation(
            slide_type,
            pt_data,
            tldr_strip=tldr_value if slide_type == "intro" else None,
            icon_offset=0,
        )
        presentation_en = _build_locale_presentation(
            slide_type,
            en_data,
            icon_offset=0,
        )

        updated = dict(slide)
        updated.update({
            "slide_index": slide_index,
            "slide_type": slide_type,
            "title": presentation_pt.get("heading", ""),
            PRESENTATION_PT_KEY: presentation_pt,
            PRESENTATION_EN_KEY: presentation_en,
            "draft_text": str(presentation_pt.get("body") or ""),
            "policy_version": str(slide.get("policy_version") or DEFAULT_PRESENTATION_POLICY_VERSION),
        })
        if image_prompt_value:
            updated["image_prompt"] = image_prompt_value
        repaired.append(updated)
    _polish_repaired_slides(repaired)
    return repaired


def _translations_from_slides(slides: list[dict[str, object]]) -> dict[int, dict[str, object]]:
    translations: dict[int, dict[str, object]] = {}
    for slide in slides:
        slide_index = int(slide.get("slide_index") or 0)
        presentation_en = _as_mapping(slide.get(PRESENTATION_EN_KEY))
        if slide_index <= 0 or presentation_en is None:
            continue
        translations[slide_index] = {
            "heading": str(presentation_en.get("heading") or ""),
            "body": str(presentation_en.get("body") or ""),
        }
    return translations


async def repair_workflow(project_id: str, *, dry_run: bool = False) -> dict[str, object]:
    settings = get_settings()
    async with AsyncSqliteSaver.from_conn_string(settings.carousel_checkpoint_sqlite_path) as checkpointer:
        engine = CarouselWorkflowEngine(checkpointer=checkpointer)
        state = await engine.get_state(project_id)
        if state is None:
            raise RuntimeError(f"No workflow state found for project {project_id}")

        raw_drafts = state.get("slide_drafts")
        if not isinstance(raw_drafts, list):
            raise RuntimeError("Workflow state has no slide_drafts to repair")

        draft_dicts = [slide for slide in raw_drafts if isinstance(slide, dict)]
        repaired_drafts = normalize_slide_drafts(draft_dicts)
        _polish_repaired_slides(repaired_drafts)
        translations_en = _translations_from_slides(repaired_drafts)
        review_updates = build_presentation_review_updates(
            repaired_drafts,
            translations_en=translations_en,
            policy_version=DEFAULT_PRESENTATION_POLICY_VERSION,
        )

        validation = review_updates.get("presentation_validation")
        blocking = False
        violation_count = 0
        if isinstance(validation, dict):
            blocking = validation.get("blocking") is True
            violations = validation.get("violations")
            violation_count = len(violations) if isinstance(violations, list) else 0

        result = {
            "project_id": project_id,
            "slide_count": len(repaired_drafts),
            "blocking": blocking,
            "violation_count": violation_count,
            "policy_version": review_updates.get("presentation_policy_version"),
        }

        if dry_run:
            result["validation"] = validation
            return result

        updates: dict[str, object] = {
            "slide_drafts": repaired_drafts,
            **review_updates,
            "translations_en": serialize_translations_en(translations_en),
            "presentation_policy_version": DEFAULT_PRESENTATION_POLICY_VERSION,
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        }
        as_node = str(state.get("current_phase") or "content")
        await engine.update_state(project_id, updates, as_node=as_node)
        return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = asyncio.run(repair_workflow(str(args.project_id), dry_run=bool(args.dry_run)))
    print(json.dumps(result, indent=2))
    if cast(bool, result.get("blocking")):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
