"""Pydantic models for the versioned carousel presentation contract."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from rag_backend.domain.constants.carousel import (
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CTA,
    SLIDE_TYPE_INTRO,
    SLIDE_TYPE_SUMMARY,
)
from rag_backend.domain.constants.carousel_presentation import (
    CANONICAL_SLIDE_COUNT,
    CLOSING_ACTION_MAX,
    CLOSING_ACTION_MIN,
    CONTENT_KIND_FEATURES,
    CONTENT_KIND_STATS,
    ERR_ACTIONS_COUNT,
    ERR_BLOCKING_VALID_REPORT,
    ERR_CONTENT_KIND_INVALID,
    ERR_FEATURES_COUNT,
    ERR_FEATURES_FORBIDDEN_FIELDS,
    ERR_FEATURES_REQUIRED,
    ERR_ICON_NAME_NOT_ALLOWLISTED,
    ERR_INSIGHT_FORBIDDEN_FIELDS,
    ERR_INSIGHT_REQUIRED,
    ERR_INVALID_REPORT_MISSING_VIOLATIONS,
    ERR_LOCALE_SLIDE_TYPE_MISMATCH,
    ERR_SLIDE_COUNT,
    ERR_SLIDE_TYPE_MISMATCH,
    ERR_STATS_COUNT,
    ERR_STATS_FORBIDDEN_FIELDS,
    ERR_STATS_REQUIRED,
    ERR_SUMMARY_POINT_COUNT,
    ERR_VALID_REPORT_HAS_VIOLATIONS,
    FEATURE_ITEM_MAX,
    FEATURE_ITEM_MIN,
    LUCIDE_ICON_ALLOWLIST,
    STAT_ITEM_COUNT,
    SUMMARY_POINT_COUNT,
    VALID_CONTENT_KINDS,
    VALIDATION_STATUS_INVALID,
    VALIDATION_STATUS_VALID,
)

_FORBID_EXTRA = ConfigDict(extra="forbid")

ContentKind = Literal["features", "stats", "insight"]
SlideType = Literal["intro", "summary", "content", "closing", "cta"]
ValidationStatus = Literal["valid", "invalid"]


def _validate_lucide_icon_name(value: str) -> str:
    normalized = value.strip()
    if normalized not in LUCIDE_ICON_ALLOWLIST:
        raise ValueError(ERR_ICON_NAME_NOT_ALLOWLISTED)
    return normalized


class FeatureItem(BaseModel):
    """Structured card with a semantic Lucide icon name."""

    model_config = _FORBID_EXTRA

    icon_name: str
    title: str
    body: str

    @field_validator("icon_name")
    @classmethod
    def _validate_icon_name(cls, value: str) -> str:
        return _validate_lucide_icon_name(value)


class StatItem(BaseModel):
    """Big-number stat card for content slides."""

    model_config = _FORBID_EXTRA

    icon_name: str
    value: str
    label: str
    detail: str | None = None

    @field_validator("icon_name")
    @classmethod
    def _validate_icon_name(cls, value: str) -> str:
        return _validate_lucide_icon_name(value)


class InsightItem(BaseModel):
    """Quoted insight card for content slides."""

    model_config = _FORBID_EXTRA

    icon_name: str
    quote: str
    attribution: str

    @field_validator("icon_name")
    @classmethod
    def _validate_icon_name(cls, value: str) -> str:
        return _validate_lucide_icon_name(value)


class ActionItem(BaseModel):
    """Closing-slide action checklist item."""

    model_config = _FORBID_EXTRA

    icon_name: str
    title: str
    body: str

    @field_validator("icon_name")
    @classmethod
    def _validate_icon_name(cls, value: str) -> str:
        return _validate_lucide_icon_name(value)


class IntroSlideCopy(BaseModel):
    model_config = _FORBID_EXTRA

    slide_type: Literal["intro"] = SLIDE_TYPE_INTRO
    heading: str
    body: str
    tldr_strip: str | None = None


class SummarySlideCopy(BaseModel):
    model_config = _FORBID_EXTRA

    slide_type: Literal["summary"] = SLIDE_TYPE_SUMMARY
    heading: str
    body: str
    summary_points: list[FeatureItem]

    @field_validator("summary_points")
    @classmethod
    def _validate_summary_points(
        cls,
        value: list[FeatureItem],
    ) -> list[FeatureItem]:
        if len(value) != SUMMARY_POINT_COUNT:
            raise ValueError(ERR_SUMMARY_POINT_COUNT)
        return value


class ContentSlideCopy(BaseModel):
    model_config = _FORBID_EXTRA

    slide_type: Literal["content"] = SLIDE_TYPE_CONTENT
    heading: str
    body: str
    content_kind: ContentKind
    features: list[FeatureItem] | None = None
    stats: list[StatItem] | None = None
    insight: InsightItem | None = None

    @field_validator("content_kind")
    @classmethod
    def _validate_content_kind(cls, value: str) -> str:
        if value not in VALID_CONTENT_KINDS:
            raise ValueError(ERR_CONTENT_KIND_INVALID)
        return value

    @model_validator(mode="after")
    def _validate_selected_structured_field(self) -> ContentSlideCopy:
        if self.content_kind == CONTENT_KIND_FEATURES:
            if self.features is None:
                raise ValueError(ERR_FEATURES_REQUIRED)
            count = len(self.features)
            if count < FEATURE_ITEM_MIN or count > FEATURE_ITEM_MAX:
                raise ValueError(ERR_FEATURES_COUNT)
            if self.stats is not None or self.insight is not None:
                raise ValueError(ERR_FEATURES_FORBIDDEN_FIELDS)
            return self
        if self.content_kind == CONTENT_KIND_STATS:
            if self.stats is None:
                raise ValueError(ERR_STATS_REQUIRED)
            if len(self.stats) != STAT_ITEM_COUNT:
                raise ValueError(ERR_STATS_COUNT)
            if self.features is not None or self.insight is not None:
                raise ValueError(ERR_STATS_FORBIDDEN_FIELDS)
            return self
        if self.insight is None:
            raise ValueError(ERR_INSIGHT_REQUIRED)
        if self.features is not None or self.stats is not None:
            raise ValueError(ERR_INSIGHT_FORBIDDEN_FIELDS)
        return self


class ClosingSlideCopy(BaseModel):
    model_config = _FORBID_EXTRA

    slide_type: Literal["closing"] = SLIDE_TYPE_CLOSING
    heading: str
    body: str
    actions: list[ActionItem]

    @field_validator("actions")
    @classmethod
    def _validate_actions(cls, value: list[ActionItem]) -> list[ActionItem]:
        count = len(value)
        if count < CLOSING_ACTION_MIN or count > CLOSING_ACTION_MAX:
            raise ValueError(ERR_ACTIONS_COUNT)
        return value


class CtaSlideCopy(BaseModel):
    model_config = _FORBID_EXTRA

    slide_type: Literal["cta"] = SLIDE_TYPE_CTA
    heading: str
    body: str
    creator_name: str
    creator_handle: str
    creator_website: str


SlidePresentationCopy = Annotated[
    IntroSlideCopy
    | SummarySlideCopy
    | ContentSlideCopy
    | ClosingSlideCopy
    | CtaSlideCopy,
    Field(discriminator="slide_type"),
]


class SlideDraft(BaseModel):
    model_config = _FORBID_EXTRA

    slide_index: int = Field(ge=1, le=7)
    slide_type: SlideType
    presentation_pt: SlidePresentationCopy
    presentation_en: SlidePresentationCopy
    long_form_notes: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_locale_parity(self) -> SlideDraft:
        if self.presentation_pt.slide_type != self.presentation_en.slide_type:
            raise ValueError(ERR_LOCALE_SLIDE_TYPE_MISMATCH)
        if self.presentation_pt.slide_type != self.slide_type:
            raise ValueError(ERR_SLIDE_TYPE_MISMATCH)
        return self


class CarouselDraftPackage(BaseModel):
    model_config = _FORBID_EXTRA

    policy_version: str
    slides: list[SlideDraft]

    @field_validator("slides")
    @classmethod
    def _validate_slide_count(cls, value: list[SlideDraft]) -> list[SlideDraft]:
        if len(value) != CANONICAL_SLIDE_COUNT:
            raise ValueError(ERR_SLIDE_COUNT)
        return value


class SlideValidationViolation(BaseModel):
    model_config = _FORBID_EXTRA

    code: str
    message: str
    slide_index: int | None = None
    locale: str | None = None
    field: str | None = None


class SlideValidationReport(BaseModel):
    model_config = _FORBID_EXTRA

    validation_status: ValidationStatus
    validated_at: datetime
    blocking: bool
    violations: list[SlideValidationViolation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_status_consistency(self) -> SlideValidationReport:
        has_violations = len(self.violations) > 0
        if self.validation_status == VALIDATION_STATUS_VALID and has_violations:
            raise ValueError(ERR_VALID_REPORT_HAS_VIOLATIONS)
        if self.validation_status == VALIDATION_STATUS_INVALID and not has_violations:
            raise ValueError(ERR_INVALID_REPORT_MISSING_VIOLATIONS)
        if self.blocking and self.validation_status == VALIDATION_STATUS_VALID:
            raise ValueError(ERR_BLOCKING_VALID_REPORT)
        return self


__all__ = [
    "ActionItem",
    "CarouselDraftPackage",
    "ClosingSlideCopy",
    "ContentSlideCopy",
    "CtaSlideCopy",
    "FeatureItem",
    "InsightItem",
    "IntroSlideCopy",
    "SlideDraft",
    "SlidePresentationCopy",
    "SlideValidationReport",
    "SlideValidationViolation",
    "StatItem",
    "SummarySlideCopy",
]
