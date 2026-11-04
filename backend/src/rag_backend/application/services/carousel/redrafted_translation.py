"""The EN translation of the slides the fail-closed retry re-drafted.

The deck is translated once, before the review. A re-drafted slide has new PT copy,
so its stored translation describes a slide that is gone. Only those slides are
translated again, in one call, from the PT copy the review will show: a labelled
scaffold is recovered first, so the raw draft never reaches the translator.

A slide the translator did not answer (the call failed or skipped it) loses its
stored translation anyway. Its EN then comes from the draft, which the gate's
language checks block, so the gate repair or the reviewer deals with it, instead of
EN silently describing the old slide. A re-draft that carries its own
``presentation_en`` needs no call: the localized builder already uses that copy.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

import structlog

from rag_backend.application.services.carousel.editorial_distribution_constants import (
    SLIDE_INDEX_KEY,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
    build_localized_slide_with_failures,
    resolve_slide_index,
)
from rag_backend.application.services.carousel.malformed_draft_normalizer import (
    normalize_slide_draft,
)
from rag_backend.application.services.carousel.provider_errors import PROVIDER_ERRORS
from rag_backend.application.services.carousel.slide_scaffold_recovery import (
    recover_parse_failures,
)

LOG_REDRAFT_TRANSLATION_MISSING = "carousel_redraft_translation_missing"

logger = structlog.get_logger(__name__)

_FAILED_CALL_ERRORS: tuple[type[Exception], ...] = (
    ValueError,
    TypeError,
    TimeoutError,
    *PROVIDER_ERRORS,
)

SlideDrafts = list[dict[str, object]]
Translations = dict[int, dict[str, object]]
SlideTranslateFn = Callable[[SlideDrafts], Awaitable[Translations]]


@dataclass(frozen=True)
class RedraftedTranslationRequest:
    """The deck after the retry, what it re-drafted and how to translate."""

    project_id: str
    slide_drafts: SlideDrafts
    redrafted: frozenset[int]
    translations_en: Mapping[int, dict[str, object]]
    translate: SlideTranslateFn


def _source(draft: dict[str, object], slide_index: int) -> dict[str, object]:
    """The draft as the translator reads it: the PT copy the review will show."""
    built, failures = build_localized_slide_with_failures(
        draft, slide_index=slide_index
    )
    (recovered,), _ = recover_parse_failures([built], failures)
    pt = as_dict(recovered.get(PRESENTATION_PT_KEY)) or {}
    return {
        **draft,
        **pt,
        SLIDE_INDEX_KEY: slide_index,
        PRESENTATION_PT_KEY: pt,
    }


def _sources(request: RedraftedTranslationRequest) -> SlideDrafts:
    """The re-drafted slides that have no EN copy of their own."""
    sources: SlideDrafts = []
    for position, draft in enumerate(request.slide_drafts, start=1):
        slide_index = resolve_slide_index(draft, position)
        if slide_index not in request.redrafted:
            continue
        normalized = normalize_slide_draft(draft)
        if as_dict(normalized.get(PRESENTATION_EN_KEY)) is None:
            sources.append(_source(normalized, slide_index))
    return sources


async def _translated(
    request: RedraftedTranslationRequest, sources: SlideDrafts
) -> Translations:
    """The answered slides; a failed call or a skipped slide is logged, never raised.

    A failed call is what the translation path raises for one: ``ValueError`` or
    ``TypeError`` once the answer does not parse (after the retries and the fallback
    model), the provider SDK's ``APIError`` (connection, timeout, status) or a
    ``TimeoutError``. Any other exception is a bug and propagates.
    """
    wanted = sorted(int(str(source[SLIDE_INDEX_KEY])) for source in sources)
    error = ""
    try:
        answered = await request.translate(sources)
    except _FAILED_CALL_ERRORS as exc:
        answered, error = {}, str(exc)
    found = {index: answered[index] for index in wanted if index in answered}
    missing = [index for index in wanted if index not in found]
    if missing:
        logger.warning(
            LOG_REDRAFT_TRANSLATION_MISSING,
            project_id=request.project_id,
            slides=missing,
            error=error,
        )
    return found


async def refresh_redrafted_translations(
    request: RedraftedTranslationRequest,
) -> Translations:
    """The translations with the re-drafted slides' EN copy made from the new PT."""
    kept = dict(request.translations_en)
    sources = _sources(request)
    if not sources:
        return kept
    for source in sources:
        kept.pop(int(str(source[SLIDE_INDEX_KEY])), None)
    return {**kept, **await _translated(request, sources)}


__all__ = [
    "LOG_REDRAFT_TRANSLATION_MISSING",
    "RedraftedTranslationRequest",
    "SlideTranslateFn",
    "refresh_redrafted_translations",
]
