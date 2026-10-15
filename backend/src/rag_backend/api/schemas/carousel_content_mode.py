"""Content-mode request/response fields for carousel projects (AE-0373, ADR-0021).

Kept apart from ``carousel.py`` so the create schema stays readable. The rules:
``pov`` needs a thesis (the model may sharpen it, never invent it), the slide-1
photo (``hook_asset_id``, PR #106 review), a known format and 8-10 slides;
``news_analysis`` (Radar IA, the default) rejects the POV-only fields and
allows 7 or 8 slides.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from rag_backend.domain.constants.carousel_cta import CTA_GOALS, DEFAULT_CTA_GOAL
from rag_backend.domain.constants.content_mode import (
    CONTENT_MODE_MAX_CHARS,
    CONTENT_MODE_NEWS_ANALYSIS,
    CONTENT_MODE_POV,
    CONTENT_MODES,
    CTA_GOAL_MAX_CHARS,
    DEFAULT_CONTENT_MODE,
    DEFAULT_POV_FORMAT,
    ERR_CONTENT_MODE_UNKNOWN,
    ERR_CTA_GOAL_UNKNOWN,
    ERR_HOOK_BLANK,
    ERR_HOOK_TOO_MANY_WORDS,
    ERR_POV_FIELDS_ON_NEWS,
    ERR_POV_FORMAT_UNKNOWN,
    ERR_POV_HOOK_PHOTO_REQUIRED,
    ERR_POV_THESIS_REQUIRED,
    ERR_SLIDE_COUNT_RANGE,
    HOOK_MAX_WORDS,
    HOOK_TEXT_MAX_CHARS,
    NEWS_SLIDE_COUNT_MAX,
    NEWS_SLIDE_COUNT_MIN,
    POV_FORMAT_MAX_CHARS,
    POV_FORMATS,
    POV_PERSONAL_PROOF_MAX_CHARS,
    POV_SLIDE_COUNT_DEFAULT,
    POV_SLIDE_COUNT_MAX,
    POV_SLIDE_COUNT_MIN,
    POV_THESIS_MAX_CHARS,
)

_POV_ONLY_FIELDS: tuple[str, ...] = (
    "pov_thesis",
    "pov_personal_proof",
    "pov_format",
    "hook_asset_id",
)
_SLIDE_RANGES: dict[str, tuple[int, int]] = {
    CONTENT_MODE_POV: (POV_SLIDE_COUNT_MIN, POV_SLIDE_COUNT_MAX),
    CONTENT_MODE_NEWS_ANALYSIS: (NEWS_SLIDE_COUNT_MIN, NEWS_SLIDE_COUNT_MAX),
}


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class ContentModeRequestFields(BaseModel):
    """Optional create fields; ``resolved_*`` give the stored values."""

    content_mode: str | None = Field(None, max_length=CONTENT_MODE_MAX_CHARS)
    pov_thesis: str | None = Field(None, max_length=POV_THESIS_MAX_CHARS)
    pov_personal_proof: str | None = Field(
        None, max_length=POV_PERSONAL_PROOF_MAX_CHARS
    )
    pov_format: str | None = Field(None, max_length=POV_FORMAT_MAX_CHARS)
    slide_count: int | None = None
    cta_goal: str | None = Field(None, max_length=CTA_GOAL_MAX_CHARS)
    persona_id: UUID | None = None
    # PR #106 review: the slide-1 photo (role hook) is required for POV.
    hook_asset_id: UUID | None = None

    @field_validator("pov_thesis", "pov_personal_proof", "pov_format")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("content_mode")
    @classmethod
    def _check_mode(cls, value: str | None) -> str | None:
        if value is not None and value not in CONTENT_MODES:
            raise ValueError(
                ERR_CONTENT_MODE_UNKNOWN.format(sorted(CONTENT_MODES), value)
            )
        return value

    @field_validator("cta_goal")
    @classmethod
    def _check_cta_goal(cls, value: str | None) -> str | None:
        if value is not None and value not in CTA_GOALS:
            raise ValueError(ERR_CTA_GOAL_UNKNOWN.format(sorted(CTA_GOALS), value))
        return value

    @property
    def resolved_mode(self) -> str:
        """The stored mode: an omitted mode is Radar IA."""
        return self.content_mode or DEFAULT_CONTENT_MODE

    def check_content_mode(self) -> None:
        """Cross-field rules; raises ``ValueError`` (a 422 in a model validator)."""
        if self.resolved_mode == CONTENT_MODE_POV:
            _check_pov(self)
        else:
            _check_news(self)
        _check_slide_count(self.resolved_mode, self.slide_count)

    def resolved_pov_format(self) -> str | None:
        """POV format (default ``opiniao``); None for Radar IA."""
        if self.resolved_mode != CONTENT_MODE_POV:
            return None
        return self.pov_format or DEFAULT_POV_FORMAT

    def resolved_slide_count(self) -> int | None:
        """POV defaults to 9 slides; Radar IA keeps None unless asked for."""
        if self.slide_count is not None:
            return self.slide_count
        return (
            POV_SLIDE_COUNT_DEFAULT if self.resolved_mode == CONTENT_MODE_POV else None
        )

    def resolved_cta_goal(self) -> str:
        """The CTA goal; follow when omitted."""
        return self.cta_goal or DEFAULT_CTA_GOAL


def _check_pov(fields: ContentModeRequestFields) -> None:
    if fields.pov_thesis is None:
        raise ValueError(ERR_POV_THESIS_REQUIRED)
    if fields.hook_asset_id is None:
        raise ValueError(ERR_POV_HOOK_PHOTO_REQUIRED)
    if fields.pov_format is not None and fields.pov_format not in POV_FORMATS:
        raise ValueError(
            ERR_POV_FORMAT_UNKNOWN.format(sorted(POV_FORMATS), fields.pov_format)
        )


def _check_news(fields: ContentModeRequestFields) -> None:
    for name in _POV_ONLY_FIELDS:
        if getattr(fields, name) is not None:
            raise ValueError(ERR_POV_FIELDS_ON_NEWS.format(name))


def _check_slide_count(mode: str, slide_count: int | None) -> None:
    if slide_count is None:
        return
    low, high = _SLIDE_RANGES[mode]
    if not low <= slide_count <= high:
        raise ValueError(ERR_SLIDE_COUNT_RANGE.format(low, high, mode, slide_count))


class ContentModeResponseFields(BaseModel):
    """Content-mode fields echoed on the project response."""

    content_mode: str = DEFAULT_CONTENT_MODE
    pov_thesis: str | None = None
    pov_personal_proof: str | None = None
    pov_format: str | None = None
    slide_count: int | None = None
    cta_goal: str | None = None
    hook_text: str | None = None
    hook_asset_id: UUID | None = None
    persona_id: str | None = None

    @field_validator("content_mode", mode="before")
    @classmethod
    def _null_is_radar(cls, value: str | None) -> str:
        return value or DEFAULT_CONTENT_MODE


class HookSelectRequest(BaseModel):
    """The owner's slide-1 hook (AE-0375): <=60 characters and <=10 words."""

    hook_text: str = Field(..., min_length=1, max_length=HOOK_TEXT_MAX_CHARS)

    @field_validator("hook_text")
    @classmethod
    def _check_hook(cls, value: str) -> str:
        stripped = " ".join(value.split())
        if not stripped:
            raise ValueError(ERR_HOOK_BLANK)
        if len(stripped.split()) > HOOK_MAX_WORDS:
            raise ValueError(ERR_HOOK_TOO_MANY_WORDS.format(HOOK_MAX_WORDS))
        return stripped


class HookSelectResponse(BaseModel):
    """The stored hook."""

    project_id: UUID
    hook_text: str


__all__ = [
    "ContentModeRequestFields",
    "ContentModeResponseFields",
    "HookSelectRequest",
    "HookSelectResponse",
]
