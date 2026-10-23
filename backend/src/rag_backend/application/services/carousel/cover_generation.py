"""Generate a slide-1 cover from the owner's library photos with Grok.

``CoverGenerationService.start`` checks the request (confirmed, a Ponto de
Vista carousel, the owner, their own photos), then, under the owner's row
lock, the caps (4 per carousel, 40 per calendar month, one pending per
carousel), records a ``pending`` generation and commits. The route hands the
run to a tracked background task (a Grok Bot job takes minutes).

``CoverGenerationRunner.run`` sends the photos, validates and stores the image
as a private creator asset with role ``cover``, and settles the row. Every
failure settles it ``failed`` with a code and leaves no asset behind. Each
step is logged with the carousel, prompt hash, model and cost, never the
prompt text or the image bytes.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

import structlog

from rag_backend.domain.constants.carousel_cover_pick import ERR_COVER_PICK_NOT_POV
from rag_backend.domain.constants.cover_generation import (
    COVER_GENERATION_MONTHLY_CAP,
    COVER_GENERATION_PER_CAROUSEL_CAP,
    ERR_COVER_GENERATION_CAROUSEL_CAP,
    ERR_COVER_GENERATION_IN_PROGRESS,
    ERR_COVER_GENERATION_MONTHLY_CAP,
    ERR_COVER_GENERATION_NOT_CONFIRMED,
    ERR_COVER_GENERATION_NOT_OWNER,
    ERR_COVER_GENERATION_PHOTO_NOT_ALLOWED,
    FAILURE_BRIDGE,
    FAILURE_INVALID_IMAGE,
    FAILURE_PHOTO_UNREADABLE,
    LOG_COVER_GENERATION,
    LOG_COVER_GENERATION_FAILED,
    LOG_COVER_GENERATION_STARTED,
    LOG_COVER_GENERATION_SUCCEEDED,
)
from rag_backend.domain.content_mode import is_pov_family
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.cover_generation import (
    CoverEditJob,
    CoverGeneration,
    CoverGenerationOutcome,
    CoverGenerationStatus,
    ReferencePhoto,
)
from rag_backend.domain.models.slide_cover import CoverAssetError
from rag_backend.domain.protocols import CoverImageEditor

logger = structlog.get_logger(__name__)


class CoverGenerationError(ValueError):
    """A refused generation; ``code`` is the public error detail."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class CoverGenerationRefusedError(CoverGenerationError):
    """A generation the caps or a running one forbid now (HTTP 409)."""


class CoverGenerationForbiddenError(CoverGenerationError):
    """Someone other than the carousel's owner (HTTP 403)."""


class CoverGenerationStore(Protocol):
    """The generation rows of one session."""

    async def lock_owner(self, owner_id: str) -> None: ...

    async def create(self, generation: CoverGeneration) -> None: ...

    async def for_project(self, project_id: str) -> tuple[CoverGeneration, ...]: ...

    async def count_owner_since(self, owner_id: str, since: datetime) -> int: ...

    async def settle(self, outcome: CoverGenerationOutcome) -> bool: ...

    async def fail_stale(self, created_before: datetime, at: datetime) -> int: ...

    async def commit(self) -> None: ...


class OwnerPhotos(Protocol):
    """The owner's library photos (role ``hook``, file present)."""

    async def photo_ids(self, owner_id: str) -> frozenset[UUID]: ...

    async def load(self, asset_ids: tuple[UUID, ...]) -> tuple[ReferencePhoto, ...]:
        """Re-encoded bytes, in order; raises ``CoverAssetError`` when unreadable."""
        ...


class CoverResults(Protocol):
    """Store a generated image as a private ``cover`` creator asset."""

    async def store(self, owner_id: str, image: bytes) -> UUID:
        """The asset id; raises ``CoverAssetError`` for an unusable image."""
        ...

    async def discard(self, asset_id: UUID) -> None: ...


@dataclass(frozen=True, kw_only=True)
class CoverGenerationConfig:
    """The model and cost recorded per generation, and when a run is lost."""

    model: str
    cost_usd: float
    stale_after_seconds: int
    now: Callable[[], datetime]


@dataclass(frozen=True, kw_only=True)
class StartCoverGeneration:
    """The owner's request, as received."""

    project: CarouselProject
    user_id: str
    photo_ids: tuple[UUID, ...]
    prompt: str
    confirmed: bool


@dataclass(frozen=True, kw_only=True)
class CoverGenerationUsage:
    """How many slots are used and the carousel's generations, newest first."""

    carousel_used: int
    month_used: int
    generations: tuple[CoverGeneration, ...]
    carousel_cap: int = COVER_GENERATION_PER_CAROUSEL_CAP
    month_cap: int = COVER_GENERATION_MONTHLY_CAP


@dataclass(frozen=True, kw_only=True)
class CoverGenerationRun:
    """What the background run needs: the row and the request."""

    generation: CoverGeneration
    photo_ids: tuple[UUID, ...]
    prompt: str


def prompt_digest(prompt: str) -> str:
    """The SHA-256 of the owner's prompt (logged instead of the text)."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def month_start(moment: datetime) -> datetime:
    """The first instant of ``moment``'s calendar month."""
    return moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _log(generation: CoverGeneration, outcome: str, **fields: object) -> None:
    logger.info(
        LOG_COVER_GENERATION,
        outcome=outcome,
        generation_id=str(generation.id),
        project_id=generation.project_id,
        prompt_sha256=generation.prompt_sha256,
        photo_count=generation.photo_count,
        model=generation.model,
        cost_usd=generation.cost_usd,
        **fields,
    )


class CoverGenerationService:
    """Usage and the start of a generation, on the request's session."""

    def __init__(
        self,
        store: CoverGenerationStore,
        photos: OwnerPhotos,
        config: CoverGenerationConfig,
    ) -> None:
        self._store = store
        self._photos = photos
        self._config = config

    async def usage(
        self, project: CarouselProject, user_id: str
    ) -> CoverGenerationUsage:
        """The caps in use and the carousel's generations (owner only)."""
        _assert_owner(project, user_id)
        _assert_pov(project)
        await self._fail_stale()
        usage = await self._usage(project, user_id)
        await self._store.commit()
        return usage

    async def start(self, command: StartCoverGeneration) -> CoverGenerationRun:
        """Record a pending generation; raises when refused."""
        if not command.confirmed:
            raise CoverGenerationError(ERR_COVER_GENERATION_NOT_CONFIRMED)
        project = command.project
        _assert_owner(project, command.user_id)
        _assert_pov(project)
        owned = await self._photos.photo_ids(command.user_id)
        if not set(command.photo_ids) <= owned:
            raise CoverGenerationError(ERR_COVER_GENERATION_PHOTO_NOT_ALLOWED)
        await self._store.lock_owner(command.user_id)
        await self._fail_stale()
        _assert_slot(await self._usage(project, command.user_id))
        generation = self._new(command)
        await self._store.create(generation)
        await self._store.commit()
        _log(generation, LOG_COVER_GENERATION_STARTED)
        return CoverGenerationRun(
            generation=generation, photo_ids=command.photo_ids, prompt=command.prompt
        )

    def _new(self, command: StartCoverGeneration) -> CoverGeneration:
        return CoverGeneration(
            id=uuid4(),
            project_id=str(command.project.id),
            owner_id=command.user_id,
            status=CoverGenerationStatus.PENDING,
            prompt_sha256=prompt_digest(command.prompt),
            photo_count=len(command.photo_ids),
            model=self._config.model,
            cost_usd=self._config.cost_usd,
            created_at=self._config.now(),
        )

    async def _usage(
        self, project: CarouselProject, owner_id: str
    ) -> CoverGenerationUsage:
        generations = await self._store.for_project(str(project.id))
        since = month_start(self._config.now())
        return CoverGenerationUsage(
            carousel_used=sum(1 for g in generations if g.counts_against_caps),
            month_used=await self._store.count_owner_since(owner_id, since),
            generations=generations,
        )

    async def _fail_stale(self) -> None:
        now = self._config.now()
        cutoff = now - timedelta(seconds=self._config.stale_after_seconds)
        await self._store.fail_stale(cutoff, now)


def _assert_owner(project: CarouselProject, user_id: str) -> None:
    if not project.owner_id or project.owner_id != user_id:
        raise CoverGenerationForbiddenError(ERR_COVER_GENERATION_NOT_OWNER)


def _assert_pov(project: CarouselProject) -> None:
    if not is_pov_family(project.content_mode):
        raise CoverGenerationError(ERR_COVER_PICK_NOT_POV)


def _assert_slot(usage: CoverGenerationUsage) -> None:
    if any(g.status is CoverGenerationStatus.PENDING for g in usage.generations):
        raise CoverGenerationRefusedError(ERR_COVER_GENERATION_IN_PROGRESS)
    if usage.carousel_used >= usage.carousel_cap:
        raise CoverGenerationRefusedError(ERR_COVER_GENERATION_CAROUSEL_CAP)
    if usage.month_used >= usage.month_cap:
        raise CoverGenerationRefusedError(ERR_COVER_GENERATION_MONTHLY_CAP)


@dataclass(frozen=True, kw_only=True)
class CoverRunDeps:
    """The ports of one background run (its own session)."""

    store: CoverGenerationStore
    photos: OwnerPhotos
    results: CoverResults
    editor: CoverImageEditor
    render_prompt: Callable[[str], str]
    now: Callable[[], datetime]


class CoverGenerationRunner:
    """Run one pending generation to ``succeeded`` or ``failed``."""

    def __init__(self, deps: CoverRunDeps) -> None:
        self._deps = deps

    async def run(self, run: CoverGenerationRun) -> CoverGenerationStatus:
        """Send, store and settle; the final status."""
        generation = run.generation
        try:
            photos = await self._deps.photos.load(run.photo_ids)
        except CoverAssetError:
            return await self._fail(generation, FAILURE_PHOTO_UNREADABLE)
        job = CoverEditJob(
            prompt=self._deps.render_prompt(run.prompt),
            photos=photos,
            project_id=generation.project_id,
        )
        try:
            image = await self._deps.editor.edit_image(job)
        except RuntimeError:
            return await self._fail(generation, FAILURE_BRIDGE)
        try:
            asset_id = await self._deps.results.store(generation.owner_id, image)
        except CoverAssetError:
            return await self._fail(generation, FAILURE_INVALID_IMAGE)
        return await self._succeed(generation, asset_id)

    async def _succeed(
        self, generation: CoverGeneration, asset_id: UUID
    ) -> CoverGenerationStatus:
        outcome = CoverGenerationOutcome(
            generation_id=generation.id, at=self._deps.now(), result_asset_id=asset_id
        )
        if not await self._deps.store.settle(outcome):
            await self._deps.results.discard(asset_id)
            await self._deps.store.commit()
            _log(generation, LOG_COVER_GENERATION_FAILED, error_code="not_pending")
            return CoverGenerationStatus.FAILED
        await self._deps.store.commit()
        _log(generation, LOG_COVER_GENERATION_SUCCEEDED, asset_id=str(asset_id))
        return CoverGenerationStatus.SUCCEEDED

    async def _fail(
        self, generation: CoverGeneration, code: str
    ) -> CoverGenerationStatus:
        outcome = CoverGenerationOutcome(
            generation_id=generation.id, at=self._deps.now(), error_code=code
        )
        await self._deps.store.settle(outcome)
        await self._deps.store.commit()
        _log(generation, LOG_COVER_GENERATION_FAILED, error_code=code)
        return CoverGenerationStatus.FAILED


__all__ = [
    "CoverGenerationConfig",
    "CoverGenerationError",
    "CoverGenerationForbiddenError",
    "CoverGenerationRefusedError",
    "CoverGenerationRun",
    "CoverGenerationRunner",
    "CoverGenerationService",
    "CoverGenerationStore",
    "CoverGenerationUsage",
    "CoverResults",
    "CoverRunDeps",
    "OwnerPhotos",
    "StartCoverGeneration",
    "month_start",
    "prompt_digest",
]
