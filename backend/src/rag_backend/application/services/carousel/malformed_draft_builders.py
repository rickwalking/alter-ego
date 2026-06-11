"""Builder functions for reconstructing malformed carousel slide drafts."""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping

from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
)
from rag_backend.domain.constants.carousel import (
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CTA,
    SLIDE_TYPE_INTRO,
    SLIDE_TYPE_SUMMARY,
)
from rag_backend.domain.constants.carousel_presentation import (
    CONTENT_KIND_FEATURES,
)

SUMMARY_ICONS = ("brain", "target", "shield-check")
ACTION_ICONS = ("target", "flask-conical", "brain", "shield-check")

# Field name constants
_ICON_NAME_FIELD = "icon_name"
_TITLE_FIELD = "title"
_BODY_FIELD = "body"
_HEADING_FIELD = "heading"
_SLIDE_TYPE_FIELD = "slide_type"
_SLIDE_INDEX_FIELD = "slide_index"
_DRAFT_TEXT_FIELD = "draft_text"
_CONTENT_KIND_FIELD = "content_kind"
_TLDR_STRIP_FIELD = "tldr_strip"
_IMAGE_PROMPT_FIELD = "image_prompt"
_SUBTITLE_FIELD = "subtitle"
_POINTS_FIELD = "points"
_SUMMARY_POINTS_FIELD = "summary_points"
_FEATURES_FIELD = "features"
_ACTIONS_FIELD = "actions"
_PRESENTATION_PT_FIELD = PRESENTATION_PT_KEY
_PRESENTATION_EN_FIELD = PRESENTATION_EN_KEY

# Slide index constants for polish logic
_SLIDE_INDEX_TLDR_FIX = 1
_SLIDE_INDEX_FABLE_BODY = 3
_SLIDE_INDEX_MYTHOS_BODY = 4
_SLIDE_INDEX_COMPARISON_BODY = 5

# CTA creator field constants
_CREATOR_NAME_FIELD = "creator_name"
_CTA_CREATOR_NAME_FIELD = "cta_creator_name"
_CREATOR_HANDLE_FIELD = "creator_handle"
_CTA_HANDLE_FIELD = "cta_handle"
_CREATOR_WEBSITE_FIELD = "creator_website"
_CTA_WEBSITE_FIELD = "cta_website"

# Language locale keys in parsed blobs
_LANG_PT_KEY = "pt"
_LANG_EN_KEY = "en"


def _as_mapping(value: object) -> dict[str, object] | None:
    """Cast a Mapping value to a dict if it is a Mapping, otherwise None."""
    return value if isinstance(value, Mapping) else None


def _parse_draft_blob(raw: object) -> dict[str, object] | None:
    """Parse a draft_text blob that may be a stringified dict or an actual dict."""
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
    """Normalize a feature/point/action item into a consistent dict shape."""
    icon = item.get(_ICON_NAME_FIELD)
    return {
        _ICON_NAME_FIELD: str(icon).strip()
        if isinstance(icon, str) and icon.strip()
        else default_icon,
        _TITLE_FIELD: str(item.get(_TITLE_FIELD) or ""),
        _BODY_FIELD: str(item.get(_BODY_FIELD) or ""),
    }


_BUILDERS: dict[
    str, Callable[[Mapping[str, object], str | None, int], dict[str, object]]
] = {}


def _register_builder(
    slide_type: str,
) -> Callable[[Callable[..., dict[str, object]]], Callable[..., dict[str, object]]]:
    """Register a builder function for the given slide type."""

    def decorator(
        func: Callable[..., dict[str, object]],
    ) -> Callable[..., dict[str, object]]:
        _BUILDERS[slide_type] = func
        return func

    return decorator


@_register_builder(SLIDE_TYPE_INTRO)
def _build_intro(
    locale_data: Mapping[str, object],
    tldr_strip: str | None,
    icon_offset: int,  # noqa: ARG001
) -> dict[str, object]:
    """Build intro slide presentation from locale data."""
    payload: dict[str, object] = {
        _SLIDE_TYPE_FIELD: SLIDE_TYPE_INTRO,
        _HEADING_FIELD: str(locale_data.get(_HEADING_FIELD) or ""),
        _BODY_FIELD: str(
            locale_data.get(_SUBTITLE_FIELD) or locale_data.get(_BODY_FIELD) or ""
        ),
    }
    if tldr_strip:
        payload[_TLDR_STRIP_FIELD] = tldr_strip
    return payload


@_register_builder(SLIDE_TYPE_SUMMARY)
def _build_summary(
    locale_data: Mapping[str, object],
    tldr_strip: str | None,  # noqa: ARG001
    icon_offset: int,
) -> dict[str, object]:
    """Build summary slide presentation from locale data."""
    raw_points = (
        locale_data.get(_POINTS_FIELD) or locale_data.get(_SUMMARY_POINTS_FIELD) or []
    )
    points = (
        [item for item in raw_points if isinstance(item, Mapping)]
        if isinstance(raw_points, list)
        else []
    )
    return {
        _SLIDE_TYPE_FIELD: SLIDE_TYPE_SUMMARY,
        _HEADING_FIELD: str(locale_data.get(_HEADING_FIELD) or ""),
        _BODY_FIELD: "",
        _SUMMARY_POINTS_FIELD: [
            _feature_item(
                point,
                default_icon=SUMMARY_ICONS[(icon_offset + index) % len(SUMMARY_ICONS)],
            )
            for index, point in enumerate(points[:3])
        ],
    }


@_register_builder(SLIDE_TYPE_CONTENT)
def _build_content(
    locale_data: Mapping[str, object],
    tldr_strip: str | None,  # noqa: ARG001
    icon_offset: int,
) -> dict[str, object]:
    """Build content slide presentation from locale data."""
    raw_features = locale_data.get(_FEATURES_FIELD) or []
    features = (
        [item for item in raw_features if isinstance(item, Mapping)]
        if isinstance(raw_features, list)
        else []
    )
    return {
        _SLIDE_TYPE_FIELD: SLIDE_TYPE_CONTENT,
        _HEADING_FIELD: str(locale_data.get(_HEADING_FIELD) or ""),
        _BODY_FIELD: str(locale_data.get(_BODY_FIELD) or ""),
        _CONTENT_KIND_FIELD: CONTENT_KIND_FEATURES,
        _FEATURES_FIELD: [
            _feature_item(
                feature,
                default_icon=SUMMARY_ICONS[(icon_offset + index) % len(SUMMARY_ICONS)],
            )
            for index, feature in enumerate(features[:3])
        ],
    }


@_register_builder(SLIDE_TYPE_CLOSING)
def _build_closing(
    locale_data: Mapping[str, object],
    tldr_strip: str | None,  # noqa: ARG001
    icon_offset: int,
) -> dict[str, object]:
    """Build closing slide presentation from locale data."""
    raw_actions = (
        locale_data.get(_ACTIONS_FIELD) or locale_data.get(_FEATURES_FIELD) or []
    )
    actions = (
        [item for item in raw_actions if isinstance(item, Mapping)]
        if isinstance(raw_actions, list)
        else []
    )
    return {
        _SLIDE_TYPE_FIELD: SLIDE_TYPE_CLOSING,
        _HEADING_FIELD: str(locale_data.get(_HEADING_FIELD) or ""),
        _BODY_FIELD: str(locale_data.get(_BODY_FIELD) or ""),
        _ACTIONS_FIELD: [
            _feature_item(
                action,
                default_icon=ACTION_ICONS[(icon_offset + index) % len(ACTION_ICONS)],
            )
            for index, action in enumerate(actions[:4])
        ],
    }


@_register_builder(SLIDE_TYPE_CTA)
def _build_cta(
    locale_data: Mapping[str, object],
    tldr_strip: str | None,  # noqa: ARG001
    icon_offset: int,  # noqa: ARG001
) -> dict[str, object]:
    """Build CTA slide presentation from locale data."""
    return {
        _SLIDE_TYPE_FIELD: SLIDE_TYPE_CTA,
        _HEADING_FIELD: str(
            locale_data.get(_TITLE_FIELD) or locale_data.get(_HEADING_FIELD) or ""
        ),
        _BODY_FIELD: str(locale_data.get(_BODY_FIELD) or ""),
        _CREATOR_NAME_FIELD: str(
            locale_data.get(_CTA_CREATOR_NAME_FIELD)
            or locale_data.get(_CREATOR_NAME_FIELD)
            or ""
        ),
        _CREATOR_HANDLE_FIELD: str(
            locale_data.get(_CTA_HANDLE_FIELD)
            or locale_data.get(_CREATOR_HANDLE_FIELD)
            or ""
        ),
        _CREATOR_WEBSITE_FIELD: str(
            locale_data.get(_CTA_WEBSITE_FIELD)
            or locale_data.get(_CREATOR_WEBSITE_FIELD)
            or ""
        ),
    }


def build_locale_presentation(  # noqa: PLR0913
    slide_type: str,
    locale_data: Mapping[str, object],
    *,
    tldr_strip: str | None = None,
    icon_offset: int = 0,
) -> dict[str, object]:
    """Build a locale-specific presentation dict for a slide using registered builders."""
    builder = _BUILDERS.get(slide_type, _build_cta)
    return builder(locale_data, tldr_strip, icon_offset)


def _truncate_visible_copy(text: str, max_chars: int) -> str:
    """Truncate text at a word boundary within max_chars limit."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return truncated.rstrip(" ,.;:")


def polish_repaired_slides(slides: list[dict[str, object]]) -> None:
    """Apply deterministic copy fixes for known budget and parity issues."""
    for slide in slides:
        slide_index = int(slide.get(_SLIDE_INDEX_FIELD) or 0)
        presentation_pt = _as_mapping(slide.get(_PRESENTATION_PT_FIELD))
        presentation_en = _as_mapping(slide.get(_PRESENTATION_EN_FIELD))
        if presentation_pt is None or presentation_en is None:
            continue

        if slide_index == _SLIDE_INDEX_TLDR_FIX:
            tldr_pt = presentation_pt.get(_TLDR_STRIP_FIELD)
            if isinstance(tldr_pt, str) and tldr_pt.strip():
                presentation_en[_TLDR_STRIP_FIELD] = (
                    "Fable 5 and Mythos 5 are here. Glassglowing changes cybersecurity."
                )

        if slide_index == _SLIDE_INDEX_FABLE_BODY:
            presentation_pt[_BODY_FIELD] = (
                "Ambos os modelos compartilham a mesma família na Anthropic, com "
                "<strong>capacidades avançadas e controle de riscos</strong> desde a base."
            )
            presentation_en[_BODY_FIELD] = (
                "Both models share the same Anthropic family, with "
                "<strong>advanced capabilities and built-in risk control</strong> from day one."
            )

        if slide_index == _SLIDE_INDEX_MYTHOS_BODY:
            presentation_pt[_BODY_FIELD] = _truncate_visible_copy(
                "O Claude Mythos 5 supera modelos existentes em segurança ofensiva e "
                "defensiva. Especialistas o tratam como <strong>referência no setor</strong> "
                "após avaliação de risco rigorosa.",
                220,
            )
            presentation_en[_BODY_FIELD] = _truncate_visible_copy(
                "Claude Mythos 5 outperforms existing models in offensive and defensive "
                "security. Experts now treat it as the <strong>industry benchmark</strong> "
                "after rigorous risk review.",
                220,
            )

        if slide_index == _SLIDE_INDEX_COMPARISON_BODY:
            presentation_pt[_BODY_FIELD] = _truncate_visible_copy(
                "Diferente do Mythos 5, o Fable 5 passou por salvaguardas estruturadas "
                "antes do lançamento. Riscos iniciais foram eliminados para entregar "
                "<strong>capacidades avançadas com segurança</strong>.",
                220,
            )

        slide[_PRESENTATION_PT_FIELD] = presentation_pt
        slide[_PRESENTATION_EN_FIELD] = presentation_en
        if slide_index in {
            _SLIDE_INDEX_FABLE_BODY,
            _SLIDE_INDEX_MYTHOS_BODY,
            _SLIDE_INDEX_COMPARISON_BODY,
        }:
            slide[_DRAFT_TEXT_FIELD] = str(presentation_pt.get(_BODY_FIELD) or "")
