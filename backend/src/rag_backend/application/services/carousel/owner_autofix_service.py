"""Owner "Fix issues": inspect a carousel, then repair and re-render it (AE-0367).

``inspect`` is read-only and cheap (no LLM): the issue lines for the Telegram
review and whether anything is fixable. ``apply`` runs on the autopilot worker
tick, never in the webhook:

1. plan the deterministic repairs over the persisted rows (+ outline/research);
2. re-translate the untranslated EN texts in one bounded call (kept on failure);
3. under the shared per-project lock (AE-0316), take the ``lock_version`` CAS
   (always, so the owner gets a fresh review revision), project the repaired
   copy onto the rows (images, prompts and notes untouched), commit, and patch
   the checkpoint's presentation copy + validation report;
4. re-render through the republish path (new artifact version, hero images
   reused), then re-inspect for what is left.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.carousel_republish import (
    engine_from_session,
)
from rag_backend.application.services.carousel.editorial_distribution_persist import (
    LocalizedCopyProjection,
    project_localized_copy_to_database,
)
from rag_backend.application.services.carousel.owner_autofix_checkpoint import (
    checkpoint_patch,
)
from rag_backend.application.services.carousel.owner_autofix_issues import (
    issue_lines,
    noun_findings,
    noun_issues,
    translation_issues,
    violation_issues,
)
from rag_backend.application.services.carousel.owner_autofix_plan import (
    AutofixPlan,
    apply_translations,
    plan_autofix,
)
from rag_backend.application.services.carousel.owner_autofix_source import (
    AutofixSource,
    AutofixSourceRequest,
    WorkflowStateStore,
    load_autofix_source,
)
from rag_backend.application.services.carousel.owner_autofix_translate import (
    EnRetranslator,
    RetranslateResult,
    retranslate_bounded,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
    AUTOFIX_STATUS_NOTHING_TO_FIX,
    ISSUE_LINE_RENDER_FAILED,
    LOG_AUTOFIX_APPLIED,
    LOG_AUTOFIX_CONFLICT,
    LOG_AUTOFIX_NOOP,
    LOG_AUTOFIX_RENDER_FAILED,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.models.carousel_conflict import CarouselConflictError
from rag_backend.domain.protocols.repositories import CarouselRepository
from rag_backend.modules.editorial.public import (
    CarouselProjectWriteOwner,
    carousel_project_lock,
)

logger = structlog.get_logger()


class CarouselRenderer(Protocol):
    """Re-render one carousel's slides and artifacts; returns its errors."""

    async def render(self, project_id: str) -> tuple[str, ...]:
        """Empty when the new artifact version is active."""
        ...


@dataclass(frozen=True)
class OwnerAutofixDeps:
    """One session's collaborators. The facade builds them."""

    db: AsyncSession
    repo: CarouselRepository
    workflow: WorkflowStateStore | None = None
    translator: EnRetranslator | None = None
    renderer: CarouselRenderer | None = None


@dataclass(frozen=True)
class AutofixInspection:
    """Issue lines for the review message and whether the fix can help."""

    lines: tuple[str, ...] = ()
    fixable: bool = False


@dataclass(frozen=True)
class AutofixApplyCommand:
    """Fix one carousel at the workflow lock version the caller read."""

    project_id: str
    expected_version: int


@dataclass(frozen=True)
class AutofixApplyResult:
    """What the fix did and what is left for a rework."""

    status: str
    slides: tuple[int, ...] = ()
    remaining: tuple[str, ...] = ()
    translation_failed: bool = False
    render_errors: tuple[str, ...] = ()


class _ConflictError(Exception):
    """Another writer holds the lock or moved the lock version."""


@dataclass(frozen=True)
class _Fix:
    source: AutofixSource
    records: list[dict[str, object]]


def _inspection(source: AutofixSource, plan: AutofixPlan) -> AutofixInspection:
    report = validate_localized_slides(
        source.records, policy_version=source.policy_version
    )
    nouns = noun_findings(source.records, source.context.vocabulary)
    lines = issue_lines([
        *violation_issues(report),
        *translation_issues(plan.retranslate),
        *noun_issues(nouns),
    ])
    return AutofixInspection(lines=lines, fixable=plan.fixable)


class OwnerAutofixService:
    """Inspect and apply the owner autofix for one carousel."""

    def __init__(self, deps: OwnerAutofixDeps) -> None:
        self._deps = deps

    async def inspect(self, project_id: str) -> AutofixInspection:
        """Issue lines and fixability. Read-only, no LLM."""
        source = await self._source(project_id)
        if source is None:
            return AutofixInspection()
        return _inspection(source, plan_autofix(source.records, source.context))

    async def apply(self, command: AutofixApplyCommand) -> AutofixApplyResult:
        """Repair, re-translate, persist, re-render.

        The lock-version CAS is taken even when nothing is fixable (a race with
        the webhook's check), so the owner always gets a fresh review revision.
        """
        source = await self._source(command.project_id)
        if source is None:
            return AutofixApplyResult(status=AUTOFIX_STATUS_NOTHING_TO_FIX)
        plan = plan_autofix(source.records, source.context)
        translation = await self._translate(plan)
        records = apply_translations(plan.records, translation.texts, source.context)
        try:
            slides = await self._persist(command, _Fix(source=source, records=records))
        except _ConflictError:
            logger.info(LOG_AUTOFIX_CONFLICT, project_id=command.project_id)
            return AutofixApplyResult(status=AUTOFIX_STATUS_CONFLICT)
        if not plan.fixable:
            logger.info(LOG_AUTOFIX_NOOP, project_id=command.project_id)
            return AutofixApplyResult(status=AUTOFIX_STATUS_NOTHING_TO_FIX)
        return await self._finish(command, slides, translation)

    async def _finish(
        self,
        command: AutofixApplyCommand,
        slides: tuple[int, ...],
        translation: RetranslateResult,
    ) -> AutofixApplyResult:
        errors = await self._render(command.project_id) if slides else ()
        remaining = (await self.inspect(command.project_id)).lines
        if errors:
            detail = errors[0]
            remaining = (ISSUE_LINE_RENDER_FAILED.format(detail=detail), *remaining)
        logger.info(
            LOG_AUTOFIX_APPLIED,
            project_id=command.project_id,
            slides=list(slides),
            remaining=len(remaining),
            translation_failed=translation.failed,
        )
        return AutofixApplyResult(
            status=AUTOFIX_STATUS_FIXED,
            slides=slides,
            remaining=remaining,
            translation_failed=translation.failed,
            render_errors=errors,
        )

    async def _source(self, project_id: str) -> AutofixSource | None:
        return await load_autofix_source(
            AutofixSourceRequest(
                repo=self._deps.repo,
                project_id=project_id,
                workflow=self._deps.workflow,
            )
        )

    async def _translate(self, plan: AutofixPlan) -> RetranslateResult:
        if self._deps.translator is None or not plan.retranslate:
            return RetranslateResult(
                texts={}, failed=bool(plan.retranslate), attempts=0
            )
        return await retranslate_bounded(self._deps.translator, plan.retranslate)

    async def _persist(
        self, command: AutofixApplyCommand, fix: _Fix
    ) -> tuple[int, ...]:
        engine = engine_from_session(self._deps.db)
        try:
            async with carousel_project_lock(
                engine, command.project_id, blocking=False
            ):
                return await self._write(command, fix)
        except CarouselConflictError as exc:
            await self._deps.db.rollback()
            raise _ConflictError from exc

    async def _write(self, command: AutofixApplyCommand, fix: _Fix) -> tuple[int, ...]:
        await self._take_cas(command)
        slides: tuple[int, ...] = ()
        if fix.records != fix.source.records:
            slides = await project_localized_copy_to_database(
                LocalizedCopyProjection(
                    db=self._deps.db,
                    project_id=command.project_id,
                    localized_slides=fix.records,
                )
            )
        await self._deps.db.commit()
        if slides:
            await self._patch_checkpoint(command.project_id, fix)
        return slides

    async def _take_cas(self, command: AutofixApplyCommand) -> None:
        owner = CarouselProjectWriteOwner(self._deps.db)
        try:
            await owner.bump_resume_lock_version(
                command.project_id, command.expected_version
            )
        except ValueError as exc:
            if str(exc) != ERR_VERSION_CONFLICT:
                raise
            await self._deps.db.rollback()
            raise _ConflictError from exc

    async def _patch_checkpoint(self, project_id: str, fix: _Fix) -> None:
        workflow = self._deps.workflow
        if workflow is None or fix.source.state is None:
            return
        patch = checkpoint_patch(
            fix.source.state, fix.records, fix.source.policy_version
        )
        if patch is not None:
            await workflow.update_workflow_state(project_id, patch)

    async def _render(self, project_id: str) -> tuple[str, ...]:
        if self._deps.renderer is None:
            return ()
        errors = await self._deps.renderer.render(project_id)
        if errors:
            logger.warning(
                LOG_AUTOFIX_RENDER_FAILED, project_id=project_id, errors=list(errors)
            )
        return errors


__all__ = [
    "AutofixApplyCommand",
    "AutofixApplyResult",
    "AutofixInspection",
    "CarouselRenderer",
    "OwnerAutofixDeps",
    "OwnerAutofixService",
]
