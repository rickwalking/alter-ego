"""The editorial side of switching slide 1 in final review.

``EditorialReviewCoverStore`` re-checks the carousel on a fresh session,
stages the generated cover, and under the project lock and the lock-version
CAS writes ``slide_cover`` only while the row still matches: in final review
(waiting, or approved there), not released, and slide 1's cover fields
unchanged since the baseline (read ``FOR UPDATE``, so an owner write that
takes no lock is never overwritten), stamping the needs-republish marker with
it: approval is refused while the marker is set, so nothing is approved
between the write and a settled render. An approved carousel's approval is
dropped in that same commit (``ApprovalReopen``, Pedro's decision
2026-11-02); without a checkpoint reopener it is refused as approved. It then
re-renders through the republish pipeline under the build lock, re-checking
the review first; a failed render rolls the cover back and renders the
previous one (``cover_review_rollback``; the approval stays dropped), and a
rollback that cannot settle is ``rollback_failed`` (the marker stays). The
release is never touched.

``reviewing_cover_task`` is the background run of the owner's website
generation: the generated-cover selection, with the review switch for a completed
carousel and the review hold the API layer composes (the autopilot's).
"""

from __future__ import annotations

import typing
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverSelection,
    AutoCoverWrite,
    ProjectAtVersion,
    cover_baseline,
)
from rag_backend.application.services.carousel.cover_review_switch import (
    ReviewHold,
    ReviewSwitch,
    ReviewSwitchOutcome,
    review_choice_refusal,
    review_refusal,
)
from rag_backend.application.services.carousel.cover_switch_guard import (
    ReopenRefusedError,
    reopens_review,
    review_state_of,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
)
from rag_backend.domain.constants.cover_autoselect import (
    REASON_AUTO_SELECT_ASSET_GONE,
    REASON_AUTO_SELECT_NO_PROJECT,
)
from rag_backend.domain.constants.cover_review_switch import (
    REASON_AUTO_SELECT_APPROVED,
    REASON_AUTO_SELECT_ROLLBACK_FAILED,
    REASON_AUTO_SELECT_ROLLED_BACK,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.cover_generation import CoverGenerationStatus
from rag_backend.domain.models.slide_cover import SlideCover, slide_cover_row
from rag_backend.modules.editorial.infrastructure.carousel_cover_autoselect import (
    with_cover_selection,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_generation import (
    CoverRunWiring,
    cover_generation_task,
)
from rag_backend.modules.editorial.infrastructure.cover_review_rollback import (
    CoverRollback,
    RenderTarget,
    render_and_settle,
    roll_back_cover,
    row_for_update,
)
from rag_backend.modules.editorial.infrastructure.review_reopen import (
    ApprovalReopen,
    CheckpointReopener,
)

if typing.TYPE_CHECKING:
    from rag_backend.application.services.carousel.cover_generation import (
        CoverGenerationRun,
    )

SessionFactory = Callable[[], AsyncSession]


class EditorialReviewCoverStore:
    """``ReviewCoverStore`` with a fresh session per switch; ``checkpoint``
    reopens an approved carousel's review (None: an approved one is refused)."""

    def __init__(
        self, sessions: SessionFactory, checkpoint: CheckpointReopener | None = None
    ) -> None:
        self._sessions = sessions
        self._checkpoint = checkpoint

    async def switch_in_review(self, command: AutoCoverWrite) -> ReviewSwitchOutcome:
        """Re-check, stage, the locked write, the re-render, then the re-check.

        A failed render, or a carousel that left the review meanwhile, is rolled
        back (``rolled_back``).
        """
        async with self._sessions() as session:
            stored = await _write(session, _ReviewCommand(command, self._checkpoint))
            if stored.status != AUTOFIX_STATUS_FIXED or stored.cover is None:
                return ReviewSwitchOutcome(status=stored.status)
            errors = await render_and_settle(
                session, RenderTarget(project_id=command.project_id, in_review=True)
            )
            reopened = stored.reopened
            if not errors:
                return ReviewSwitchOutcome(
                    status=AUTOFIX_STATUS_FIXED, reopened=reopened
                )
            rollback = CoverRollback(
                project_id=command.project_id,
                switched=stored.cover,
                previous=stored.previous,
                render_errors=errors,
            )
            if await roll_back_cover(session, rollback):
                return ReviewSwitchOutcome(
                    status=REASON_AUTO_SELECT_ROLLED_BACK,
                    render_errors=errors,
                    reopened=reopened,
                )
            return ReviewSwitchOutcome(
                status=REASON_AUTO_SELECT_ROLLBACK_FAILED,
                render_errors=errors,
                lock_version=await _version(session, command.project_id),
                reopened=reopened,
            )


async def _version(session: AsyncSession, project_id: str) -> int | None:
    row = await row_for_update(session, project_id)
    version = int(row.lock_version or 1) if row is not None else None
    await session.rollback()
    return version


async def _load(session: AsyncSession, project_id: str) -> ProjectAtVersion | None:
    from rag_backend.modules.editorial.infrastructure import (
        CarouselProjectWriteOwner,
        LegacyCarouselAcl,
    )

    acl = LegacyCarouselAcl(session, CarouselProjectWriteOwner(session))
    view = await acl.load_editorial(project_id)
    if view is None:
        return None
    return ProjectAtVersion(
        project=view.project.project,
        lock_version=view.lock_version,
        workflow_status=view.project.workflow.workflow_status,
    )


@dataclass(frozen=True, kw_only=True)
class _Stored:
    """The write's status; on success the cover written, the one before it,
    and whether the approval was dropped with it."""

    status: str
    cover: SlideCover | None = None
    previous: SlideCover | None = None
    reopened: bool = False


@dataclass(frozen=True)
class _ReviewCommand:
    """The website's write and the checkpoint reopen of an approved carousel."""

    write: AutoCoverWrite
    checkpoint: CheckpointReopener | None


def _refusal(found: ProjectAtVersion, command: _ReviewCommand) -> str | None:
    """The review refusal, the owner's choice, or approved with no reopener."""
    refusal = review_refusal(found) or review_choice_refusal(
        found.project, command.write.baseline, command.write.asset_id
    )
    if refusal is not None or command.checkpoint is not None:
        return refusal
    if reopens_review(review_state_of(found.project, found.workflow_status)):
        return REASON_AUTO_SELECT_APPROVED
    return None


async def _write(session: AsyncSession, command: _ReviewCommand) -> _Stored:
    found = await _load(session, command.write.project_id)
    if found is None:
        return _Stored(status=REASON_AUTO_SELECT_NO_PROJECT)
    refusal = _refusal(found, command)
    if refusal is not None:
        return _Stored(status=refusal)
    cover = await _generated_cover(session, command.write)
    if cover is None or not await _stage(session, (found.project, cover)):
        return _Stored(status=REASON_AUTO_SELECT_ASSET_GONE)
    return await _locked(session, _ReviewWrite(command=command, cover=cover))


async def _generated_cover(
    session: AsyncSession, command: AutoCoverWrite
) -> SlideCover | None:
    """The carousel's generated cover ``asset_id`` (file present), as ai_image."""
    from rag_backend.domain.constants.slide_cover import COVER_KIND_AI_IMAGE
    from rag_backend.modules.editorial.infrastructure.carousel_cover_generation import (
        EditorialGeneratedCovers,
    )

    covers = await EditorialGeneratedCovers(session).covers(command.project_id)
    asset = next((item for item in covers if item.id == command.asset_id), None)
    if asset is None:
        return None
    return SlideCover(
        asset_id=asset.id, kind=COVER_KIND_AI_IMAGE, staged_path=asset.relative_path
    )


async def _stage(
    session: AsyncSession, target: tuple[CarouselProject, SlideCover]
) -> bool:
    from rag_backend.modules.editorial.infrastructure.carousel_cover import (
        stage_slide_cover,
    )

    project, cover = target
    return await stage_slide_cover(session, replace(project, slide_cover=cover))


@dataclass(frozen=True, kw_only=True)
class _ReviewWrite:
    command: _ReviewCommand
    cover: SlideCover


async def _locked(session: AsyncSession, write: _ReviewWrite) -> _Stored:
    """Project lock + the unchanged lock-version CAS; a held lock is a conflict."""
    from rag_backend.application.services.carousel.owner_autofix_lock import (
        AutofixConflictError,
        LockedWrite,
        write_locked,
    )

    target = LockedWrite(
        project_id=write.command.write.project_id,
        expected_version=write.command.write.expected_version,
    )
    try:
        return await write_locked(session, target, lambda: _store(session, write))
    except AutofixConflictError:
        return _Stored(status=AUTOFIX_STATUS_CONFLICT)


async def _store(session: AsyncSession, write: _ReviewWrite) -> _Stored:
    """Write ``slide_cover`` while the locked row still allows it, else roll back.

    The needs-republish marker is stamped in the same commit: approval is
    refused while it is set (website route and Telegram), and only a settled
    render clears it. A process that dies before the render leaves the marker
    for the republish sweep, which renders the carousel while approval is still
    refused; the held Telegram review is escalated by the worker.
    """
    project_id = write.command.write.project_id
    row = await row_for_update(session, project_id)
    if row is None:
        await session.rollback()
        return _Stored(status=REASON_AUTO_SELECT_NO_PROJECT)
    found = ProjectAtVersion(
        project=row.to_entity(),
        lock_version=int(row.lock_version or 1),
        workflow_status=str(row.workflow_status or ""),
    )
    refusal = _refusal(found, write.command)
    if refusal is not None:
        await session.rollback()
        return _Stored(status=refusal)
    try:
        reopened = await _reopen(session, write.command, found)
    except ReopenRefusedError as refused:
        await session.rollback()
        return _Stored(status=refused.reason)
    previous = found.project.slide_cover
    row.slide_cover = slide_cover_row(write.cover)
    row.needs_republish_since = datetime.now(UTC)
    await session.commit()
    return _Stored(
        status=AUTOFIX_STATUS_FIXED,
        cover=write.cover,
        previous=previous,
        reopened=reopened,
    )


async def _reopen(
    session: AsyncSession, command: _ReviewCommand, found: ProjectAtVersion
) -> bool:
    """Drop an approved carousel's approval in this transaction (True)."""
    state = review_state_of(found.project, found.workflow_status)
    if command.checkpoint is None or not reopens_review(state):
        return False
    await ApprovalReopen(session, command.checkpoint).reopen(command.write.project_id)
    return True


@dataclass(frozen=True, kw_only=True)
class CoverReviewTarget:
    """The carousel as the request loaded it, the review hold to use, and the
    checkpoint reopen of an approved carousel (None: it is refused)."""

    project: CarouselProject
    hold: ReviewHold
    checkpoint: CheckpointReopener | None = None


def reviewing_cover_task(
    wiring: CoverRunWiring, run: CoverGenerationRun, target: CoverReviewTarget
) -> Callable[[], Awaitable[CoverGenerationStatus]]:
    """The run, then the selection; a completed carousel in final review switches.

    The baseline is slide 1's cover as the request loaded it, so a change the
    owner makes while the job runs wins.
    """
    from rag_backend.infrastructure.database.config import get_session_maker

    selection = AutoCoverSelection(
        project_id=str(target.project.id),
        generation_id=run.generation.id,
        baseline=cover_baseline(target.project),
        review=ReviewSwitch(
            store=EditorialReviewCoverStore(get_session_maker(), target.checkpoint),
            hold=target.hold,
        ),
    )
    return with_cover_selection(cover_generation_task(wiring, run), selection)


__all__ = ["CoverReviewTarget", "EditorialReviewCoverStore", "reviewing_cover_task"]
