"""Pure helpers and the container choice for the Instagram publish job.

Kept beside ``publish_job.py`` so neither file exceeds the 400-line limit.

Approve makes the run ``publishing`` before the release write lands, so the
``_RELEASE_PENDING`` reasons mean "wait", not "fail".
"""

from __future__ import annotations

from datetime import datetime, timedelta

from rag_backend.domain.constants.carousel_workflow import (
    ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.instagram_publish import PUBLISH_RESULT_PUBLISHED
from rag_backend.modules.autopilot.constants import REASON_CAROUSEL_NOT_PUBLIC
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.ports import (
    CarouselPublishSnapshot,
    InstagramGraphGateway,
)
from rag_backend.modules.autopilot.domain.publish import (
    CarouselMedia,
    DueFacts,
    ManualPublishOutcome,
    PublishAction,
    PublishFacts,
    PublishGate,
    StoredContainer,
    choose_publish_action,
    is_publish_due,
)
from rag_backend.modules.autopilot.domain.story import ContainerProbe
from rag_backend.modules.autopilot.recovery_constants import RELEASE_GRACE_SECONDS

_RELEASE_PENDING = frozenset({
    REASON_CAROUSEL_NOT_PUBLIC,
    ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH,
})


def due_runs(runs: list[AutopilotRun], now: datetime) -> list[AutopilotRun]:
    """Publishing runs whose backoff has elapsed, in scan order."""
    return [
        run
        for run in runs
        if is_publish_due(
            DueFacts(attempts=run.publish_attempts, updated_at=run.updated_at, now=now)
        )
    ]


def stored_container(run: AutopilotRun) -> StoredContainer | None:
    """The run's container with its creation time, when both are stored."""
    if not run.ig_container_id or run.ig_container_created_at is None:
        return None
    return StoredContainer(
        container_id=run.ig_container_id, created_at=run.ig_container_created_at
    )


async def reusable_container(
    gateway: ContainerProbe,
    stored: StoredContainer | None,
    now: datetime,
) -> StoredContainer | None:
    """A container to finish instead of creating one, or None to create.

    A fresh container is resumed. An expired one is resumed only when Graph
    reports it ``PUBLISHED`` (a crash after ``media_publish``), so its media is
    recovered instead of the carousel being posted again (QA r2 R4a).
    """
    if stored is None:
        return None
    facts = PublishFacts(
        ig_post_id=None,
        ig_container_id=stored.container_id,
        container_created_at=stored.created_at,
        now=now,
    )
    if choose_publish_action(facts) == PublishAction.RESUME_CONTAINER:
        return stored
    if await gateway.was_published(stored):
        return stored
    return None


def release_pending(run: AutopilotRun, reason: str | None, now: datetime) -> bool:
    """True while an approved run waits for the release to make it public."""
    if reason not in _RELEASE_PENDING or run.updated_at is None:
        return False
    return now - run.updated_at < timedelta(seconds=RELEASE_GRACE_SECONDS)


def media_for(
    snapshot: CarouselPublishSnapshot | None,
    override: CarouselMedia | None,
) -> CarouselMedia | None:
    """The owner's media when given, else the carousel's own."""
    if override is not None:
        return override
    if snapshot is None:
        return None
    return CarouselMedia(caption=snapshot.caption, image_urls=snapshot.image_urls)


def gate_for(
    snapshot: CarouselPublishSnapshot | None, media: CarouselMedia | None
) -> PublishGate:
    """Local pre-check facts for ``gate_reason``."""
    if snapshot is None:
        return PublishGate(
            project_found=False,
            base_url_configured=False,
            workflow_status="",
            status="",
            is_public=False,
            image_count=0,
            has_caption=False,
        )
    count = len(snapshot.image_urls) if media is None else len(media.image_urls)
    caption = snapshot.caption if media is None else media.caption
    return PublishGate(
        project_found=True,
        base_url_configured=snapshot.base_url_configured,
        workflow_status=snapshot.workflow_status,
        status=snapshot.status,
        is_public=snapshot.is_public,
        image_count=count,
        has_caption=bool(caption.strip()),
    )


def can_step(run: AutopilotRun | None, gateway: InstagramGraphGateway) -> bool:
    """True when the run is publishing and the gateway can pause mid-flight."""
    if run is None or run.state is not AutopilotRunState.PUBLISHING:
        return False
    return gateway.can_resume()


def should_record(run: AutopilotRun | None, status: str, post_id: str | None) -> bool:
    """True when an atomic publish for a publishing run returned a post id."""
    if run is None or run.state is not AutopilotRunState.PUBLISHING:
        return False
    return status == PUBLISH_RESULT_PUBLISHED and post_id is not None


def outcome_of(
    status: str, post_id: str | None, error: str | None
) -> ManualPublishOutcome:
    """The HTTP-shaped outcome of one publish."""
    return ManualPublishOutcome(status=status, ig_post_id=post_id, error_message=error)
