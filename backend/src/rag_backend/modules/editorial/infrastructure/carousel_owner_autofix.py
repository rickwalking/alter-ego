"""The owner "Fix issues" seam the autopilot drives in-process (AE-0367).

``inspect_owner_issues`` is read-only (the webhook and the review message use
it); ``run_owner_autofix`` repairs, re-translates untranslated EN, persists and
re-renders (the worker tick uses it). Both delegate to the carousel
application service, imported lazily like the rest of the automation seam
(the editorial facade loads while the ORM registry is still initialising).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.editorial.infrastructure.carousel_automation import (
    EditorialWorkflowEngine,
)

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.owner_autofix_service import (
        OwnerAutofixService,
    )


@dataclass(frozen=True, kw_only=True)
class OwnerAutofixRequest:
    """One carousel; the engine reads/patches its checkpoint when given."""

    session: AsyncSession
    project_id: str
    engine: EditorialWorkflowEngine | None = None
    expected_version: int = 0


@dataclass(frozen=True, kw_only=True)
class OwnerIssues:
    """Issue lines for the review message and whether the fix can help."""

    lines: tuple[str, ...] = ()
    fixable: bool = False


@dataclass(frozen=True, kw_only=True)
class OwnerAutofixReport:
    """Outcome of one fix. ``status`` is one of ``AUTOFIX_STATUS_*``."""

    status: str
    slides: tuple[int, ...] = ()
    remaining: tuple[str, ...] = ()
    translation_failed: bool = False
    render_errors: tuple[str, ...] = ()


class _RepublishRenderer:
    """Re-render through the AE-0313 republish path (hero images reused)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def render(self, project_id: str) -> tuple[str, ...]:
        """New artifact version, or the errors that prevented it."""
        from rag_backend.application.services.carousel.carousel_republish import (
            republish_completed_carousel,
        )
        from rag_backend.domain.models.carousel_conflict import CarouselConflictError

        try:
            result = await republish_completed_carousel(self._session, project_id)
        except CarouselConflictError as exc:
            return (exc.conflict.code,)
        except (ValueError, TypeError, OSError) as exc:
            return (str(exc),)
        return result.errors


def _service(request: OwnerAutofixRequest, *, for_apply: bool) -> OwnerAutofixService:
    from rag_backend.application.services.carousel.owner_autofix_service import (
        OwnerAutofixDeps,
        OwnerAutofixService,
    )
    from rag_backend.application.services.carousel.owner_autofix_translate import (
        LlmEnRetranslator,
        LlmRetranslatorConfig,
    )
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )
    from rag_backend.infrastructure.llm.json_utils import extract_json
    from rag_backend.infrastructure.monitoring_langfuse import (
        get_langfuse_runnable_config,
    )

    engine = request.engine
    translator = None
    if for_apply and engine is not None:
        translator = LlmEnRetranslator(
            LlmRetranslatorConfig(
                llm=engine.chat_model,
                parse_json=extract_json,
                runnable_config=get_langfuse_runnable_config(),
            )
        )
    return OwnerAutofixService(
        OwnerAutofixDeps(
            db=request.session,
            repo=PostgresCarouselRepository(session=request.session),
            workflow=engine,
            translator=translator,
            renderer=_RepublishRenderer(request.session) if for_apply else None,
        )
    )


async def inspect_owner_issues(request: OwnerAutofixRequest) -> OwnerIssues:
    """Issue lines + fixability for one carousel. No LLM, no writes."""
    found = await _service(request, for_apply=False).inspect(request.project_id)
    return OwnerIssues(lines=found.lines, fixable=found.fixable)


async def run_owner_autofix(request: OwnerAutofixRequest) -> OwnerAutofixReport:
    """Repair, re-translate, persist and re-render one carousel."""
    from rag_backend.application.services.carousel.owner_autofix_service import (
        AutofixApplyCommand,
    )

    result = await _service(request, for_apply=True).apply(
        AutofixApplyCommand(
            project_id=request.project_id,
            expected_version=request.expected_version,
        )
    )
    return OwnerAutofixReport(
        status=result.status,
        slides=result.slides,
        remaining=result.remaining,
        translation_failed=result.translation_failed,
        render_errors=result.render_errors,
    )


__all__ = [
    "OwnerAutofixReport",
    "OwnerAutofixRequest",
    "OwnerIssues",
    "inspect_owner_issues",
    "run_owner_autofix",
]
