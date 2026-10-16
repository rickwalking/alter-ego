"""Carousel fields of an autopilot run (AE-0377, split from the driver).

PR #106 review: a POV run carries the scout's format and slide count (the
defaults were applied when the spec was built) and its slide-1 photo; every
run carries the autopilot persona, so the content phase scores voice.
"""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID

from rag_backend.domain.constants.content_mode import DEFAULT_POV_FORMAT
from rag_backend.domain.constants.presentation_policy import (
    CREATE_TIME_NEWS_PRESENTATION_POLICY_VERSION,
    CREATE_TIME_POV_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.content_mode import is_pov_family, is_pov_news
from rag_backend.domain.models.news_quote import NewsQuote
from rag_backend.modules.autopilot.constants import (
    SOURCE_FIELD_TITLE,
    SOURCE_FIELD_TYPE,
)
from rag_backend.modules.autopilot.domain.gate import ProjectSpec
from rag_backend.modules.editorial.public import (
    AutomationStart,
    ResearchSourceType,
    as_uuid,
)

_CONTENT = "content"


class PovFields(TypedDict):
    pov_thesis: str | None
    pov_format: str | None
    slide_count: int | None
    hook_asset_id: UUID | None
    persona_id: str | None
    pov_quotes: tuple[NewsQuote, ...]
    pov_sources: tuple[str, ...]


def _is_pov(spec: ProjectSpec) -> bool:
    """AE-0406: ``pov`` and ``pov_news`` both build a POV carousel."""
    return is_pov_family(spec.content_mode)


def policy_version_for(spec: ProjectSpec) -> str:
    if _is_pov(spec):
        return CREATE_TIME_POV_PRESENTATION_POLICY_VERSION
    return CREATE_TIME_NEWS_PRESENTATION_POLICY_VERSION


def pov_fields_for(spec: ProjectSpec) -> PovFields:
    if not _is_pov(spec):
        return PovFields(
            pov_thesis=None,
            pov_format=None,
            slide_count=None,
            hook_asset_id=None,
            persona_id=spec.persona_id,
            pov_quotes=(),
            pov_sources=(),
        )
    news = is_pov_news(spec.content_mode)
    return PovFields(
        pov_thesis=spec.pov_thesis,
        pov_format=spec.pov_format or DEFAULT_POV_FORMAT,
        slide_count=spec.slide_count,
        hook_asset_id=as_uuid(spec.hook_asset_id),
        persona_id=spec.persona_id,
        # AE-0406: the verified quotes and the sources of the caption footer.
        pov_quotes=spec.quotes if news else (),
        pov_sources=spec.sources if news else (),
    )


def start_input_for(spec: ProjectSpec) -> AutomationStart:
    """The unattended workflow start, voiced by the spec's persona."""
    return AutomationStart(
        topic=spec.topic,
        audience=spec.audience,
        brief=spec.brief,
        sources=_source_rows(spec.sources),
        user_id=spec.owner_user_id,
        persona_id=spec.persona_id,
    )


def _source_rows(sources: tuple[str, ...]) -> tuple[dict[str, str], ...]:
    kind = ResearchSourceType.DOCUMENTATION.value
    return tuple(_source_row(url, kind) for url in sources)


def _source_row(url: str, kind: str) -> dict[str, str]:
    return {
        SOURCE_FIELD_TITLE: url,
        _CONTENT: url,
        SOURCE_FIELD_TYPE: kind,
    }


__all__ = ["PovFields", "policy_version_for", "pov_fields_for", "start_input_for"]
