"""Instagram publish job idempotency, resume, and error policy.

Gherkin: tests/features/autopilot_instagram_publish.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from rag_backend.domain.constants.carousel import CAROUSEL_STATUS_COMPLETED
from rag_backend.domain.constants.carousel_workflow import (
    ERR_CAROUSEL_NOT_COMPLETED,
    ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_IMAGE_COUNT_INVALID,
)
from rag_backend.modules.autopilot.application.manual_publish import (
    ManualInstagramPublish,
)
from rag_backend.modules.autopilot.application.publish_job import (
    InstagramPublishJob,
    PublishJobDependencies,
)
from rag_backend.modules.autopilot.constants import (
    CALLBACK_RETRY_PREFIX,
    NOTICE_PUBLISH_FAILED,
    NOTICE_PUBLISHED,
    PAYLOAD_RETRY_CALLBACK,
    REASON_ATTEMPTS_EXHAUSTED,
    REASON_CAROUSEL_MISSING,
    REASON_CAROUSEL_NOT_PUBLIC,
    REASON_IG_LOGIN_ABSENT,
    REASON_PUBLIC_BASE_URL_MISSING,
    REASON_QUOTA_EXHAUSTED,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.ports import CarouselPublishSnapshot
from rag_backend.modules.autopilot.domain.publish import (
    AtomicPublishResult,
    CarouselMedia,
    ManualPublishCommand,
    PublishAttemptCommand,
    PublishNotice,
    RunListQuery,
    SaveContainerCommand,
    SavePostCommand,
    StoredContainer,
)
from rag_backend.modules.autopilot.domain.publish_claims import (
    ManualClaim,
    ManualContainer,
    ManualRecord,
    RunClaim,
)
from rag_backend.modules.autopilot.infrastructure.publish_notifier import _record
from rag_backend.modules.autopilot.recovery_constants import RELEASE_GRACE_SECONDS

_NOW = datetime(2026, 10, 13, 15, 0, tzinfo=UTC)
_PROJECT = "carousel-1"
_SEVEN = tuple(f"https://public.test/slide_{i}.jpg" for i in range(1, 8))


def _run() -> AutopilotRun:
    return AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=uuid4(),
        carousel_project_id=_PROJECT,
        state=AutopilotRunState.PUBLISHING,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
        updated_at=_NOW,
    )


def _snapshot() -> CarouselPublishSnapshot:
    return CarouselPublishSnapshot(
        workflow_status=WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
        status=CAROUSEL_STATUS_COMPLETED,
        is_public=True,
        caption="caption",
        image_urls=_SEVEN,
        base_url_configured=True,
    )


class _Clock:
    def __init__(self) -> None:
        self.current = _NOW

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: int) -> None:
        self.current += timedelta(seconds=seconds)


@dataclass
class _Repo:
    runs: dict[UUID, AutopilotRun] = field(default_factory=dict)
    commits: int = 0
    order: list[str] = field(default_factory=list)

    async def list_by_state(self, query: RunListQuery) -> list[AutopilotRun]:
        matched = [run for run in self.runs.values() if run.state == query.state]
        return matched[: query.limit]

    async def find_by_carousel(self, project_id: str) -> AutopilotRun | None:
        for run in self.runs.values():
            if run.carousel_project_id == project_id:
                return run
        return None

    async def save_container(self, command: SaveContainerCommand) -> bool:
        run = self.runs[command.run_id]
        self.runs[command.run_id] = replace(
            run,
            ig_container_id=command.container_id,
            ig_container_created_at=command.created_at,
            updated_at=command.created_at,
        )
        return True

    async def save_post(self, command: SavePostCommand) -> bool:
        run = self.runs[command.run_id]
        permalink = (
            run.ig_permalink if command.ig_permalink is None else command.ig_permalink
        )
        self.runs[command.run_id] = replace(
            run,
            ig_post_id=command.ig_post_id,
            ig_permalink=permalink,
        )
        return True

    async def record_attempt(self, command: PublishAttemptCommand) -> bool:
        run = self.runs[command.run_id]
        self.runs[command.run_id] = replace(
            run,
            publish_attempts=command.attempts,
            state_reason=command.reason,
            updated_at=command.at,
        )
        return True

    async def add(self, run: AutopilotRun) -> None:
        self.runs[run.run_id] = run

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        return self.runs.get(run_id)

    async def transition(self, command: TransitionCommand) -> bool:
        run = self.runs[command.run_id]
        if run.state is not command.expected:
            return False
        self.runs[command.run_id] = replace(
            run, state=command.new, state_reason=command.reason
        )
        return True

    async def commit(self) -> None:
        self.order.append("commit")
        self.commits += 1


@dataclass
class _Claims:
    """In-memory publish claims (QA r1 H1). ``held`` simulates another caller."""

    held: set[UUID] = field(default_factory=set)
    manual: dict[str, ManualRecord] = field(default_factory=dict)
    manual_held: set[str] = field(default_factory=set)
    released: list[UUID] = field(default_factory=list)
    saved_containers: list[ManualContainer] = field(default_factory=list)

    async def claim_run(self, claim: RunClaim) -> bool:
        if claim.run_id in self.held:
            return False
        self.held.add(claim.run_id)
        return True

    async def take_over_held(self, claim: RunClaim) -> bool:
        self.held.add(claim.run_id)
        return True

    async def release_run(self, run_id: UUID) -> None:
        self.held.discard(run_id)
        self.released.append(run_id)

    async def manual_record(self, project_id: str) -> ManualRecord | None:
        return self.manual.get(project_id)

    async def claim_manual(self, claim: ManualClaim) -> bool:
        if claim.project_id in self.manual_held:
            return False
        self.manual_held.add(claim.project_id)
        return True

    async def finish_manual(self, record: ManualRecord) -> None:
        self.manual[record.project_id] = record
        self.manual_held.discard(record.project_id)

    async def save_manual_container(self, container: ManualContainer) -> None:
        self.saved_containers.append(container)
        self.manual[container.project_id] = ManualRecord(
            project_id=container.project_id,
            state="publishing",
            ig_post_id=None,
            ig_permalink=None,
            error=None,
            ig_container_id=container.container_id,
            ig_container_created_at=container.created_at,
        )


class _Gateway:
    def __init__(self) -> None:
        self.opens = 0
        self.finishes = 0
        self.permalink_calls = 0
        self.atomics = 0
        self.last_container: str | None = None
        self.resume = True
        self.token = "IGAA-token"
        self.configured = True
        self.quota = 25
        self.fail_open: InstagramCallError | None = None
        self.fail_finish: InstagramCallError | None = None
        self.fail_permalink = False
        self.order: list[str] = []
        # QA r2 R4: an expired stored container may already be published.
        self.published_before = False
        self.checked: list[str] = []
        self.crash_finish = False

    def can_resume(self) -> bool:
        return self.resume

    async def current_token(self) -> str:
        return self.token

    def user_configured(self) -> bool:
        return self.configured

    async def quota_remaining(self) -> int:
        return self.quota

    async def open_carousel(self, media: CarouselMedia) -> str:
        del media
        self.opens += 1
        self.order.append("open")
        if self.fail_open is not None:
            raise self.fail_open
        return "container-new"

    async def was_published(self, container: StoredContainer) -> bool:
        self.checked.append(container.container_id)
        return self.published_before

    async def container_status(self, container: StoredContainer) -> str:
        self.checked.append(container.container_id)
        return ""

    async def finish_container(self, container: StoredContainer) -> str:
        self.finishes += 1
        self.last_container = container.container_id
        if self.crash_finish:
            raise RuntimeError("worker died mid-publish")
        self.order.append("finish")
        if self.fail_finish is not None:
            raise self.fail_finish
        return "post-1"

    async def permalink(self, media_id: str) -> str:
        del media_id
        self.permalink_calls += 1
        if self.fail_permalink:
            raise InstagramCallError(status_code=500, error_code="503", transient=True)
        return "https://instagram.com/p/abc"

    async def publish_atomic(self, media: CarouselMedia) -> AtomicPublishResult:
        del media
        self.atomics += 1
        return AtomicPublishResult(
            status="published", post_id="atomic-post", error_message=None
        )


class _Source:
    def __init__(self, snapshot: CarouselPublishSnapshot | None) -> None:
        self.snapshot = snapshot

    async def load(self, project_id: str) -> CarouselPublishSnapshot | None:
        del project_id
        return self.snapshot


class _Notifier:
    def __init__(self) -> None:
        self.notices: list[PublishNotice] = []

    async def notify(self, notice: PublishNotice) -> None:
        self.notices.append(notice)


def _deps(
    repo: _Repo,
    gateway: _Gateway,
    source: _Source,
    clock: _Clock,
    notifier: _Notifier,
    claims: _Claims | None = None,
) -> PublishJobDependencies:
    return PublishJobDependencies(
        runs=repo,
        source=source,
        gateway=gateway,
        notifier=notifier,
        clock=clock,
        checkpoint=repo,
        claims=claims if claims is not None else _Claims(),
    )


def _job(
    repo: _Repo,
    gateway: _Gateway,
    source: _Source,
    clock: _Clock,
    notifier: _Notifier,
) -> InstagramPublishJob:
    return InstagramPublishJob(_deps(repo, gateway, source, clock, notifier))


def _manual(
    repo: _Repo,
    gateway: _Gateway,
    source: _Source,
    claims: _Claims | None = None,
) -> ManualInstagramPublish:
    deps = _deps(repo, gateway, source, _Clock(), _Notifier(), claims)
    return ManualInstagramPublish(deps)


def _store(repo: _Repo, run: AutopilotRun) -> AutopilotRun:
    repo.runs[run.run_id] = run
    return run


@pytest.mark.unit
class TestApprovedCarouselPostedOnce:
    """Scenario: Approved carousel is posted once."""

    async def test_two_ticks_publish_once(self) -> None:
        repo, gateway, clock = _Repo(), _Gateway(), _Clock()
        run = _store(repo, _run())
        job = _job(repo, gateway, _Source(_snapshot()), clock, _Notifier())

        assert await job.tick() == 1
        assert await job.tick() == 0

        stored = repo.runs[run.run_id]
        assert gateway.finishes == 1
        assert gateway.opens == 1
        assert len(_snapshot().image_urls) == 7
        assert stored.state is AutopilotRunState.PUBLISHED
        assert stored.ig_post_id == "post-1"
        assert stored.ig_permalink == "https://instagram.com/p/abc"
        assert gateway.order == ["open", "finish"]
        assert repo.order[0] == "commit"


@pytest.mark.unit
class TestCrashAfterContainer:
    """Scenario: Crash after container creation."""

    async def test_reuses_the_stored_container(self) -> None:
        repo, gateway = _Repo(), _Gateway()
        run = _store(
            repo,
            replace(
                _run(), ig_container_id="container-kept", ig_container_created_at=_NOW
            ),
        )
        job = _job(repo, gateway, _Source(_snapshot()), _Clock(), _Notifier())

        await job.tick()

        assert gateway.opens == 0
        assert gateway.last_container == "container-kept"
        assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISHED


@pytest.mark.unit
class TestPermanentMetaError:
    """Scenario: Permanent Meta error."""

    async def test_error_36003_fails_and_offers_retry(self) -> None:
        repo, gateway, notifier = _Repo(), _Gateway(), _Notifier()
        gateway.fail_open = InstagramCallError(
            status_code=400, error_code="36003", transient=False
        )
        run = _store(repo, _run())
        job = _job(repo, gateway, _Source(_snapshot()), _Clock(), notifier)

        await job.tick()

        stored = repo.runs[run.run_id]
        assert stored.state is AutopilotRunState.PUBLISH_FAILED
        assert stored.state_reason == "36003"
        assert notifier.notices[0].offer_retry is True
        assert notifier.notices[0].error_code == "36003"
        assert notifier.notices[0].outcome == NOTICE_PUBLISH_FAILED
        record = _record(notifier.notices[0])
        assert (
            record.payload[PAYLOAD_RETRY_CALLBACK]
            == f"{CALLBACK_RETRY_PREFIX}{run.run_id}"
        )


@pytest.mark.unit
class TestTransientRetry:
    """Scenario: Transient Meta error is retried then failed."""

    async def test_three_attempts_then_notify(self) -> None:
        repo, gateway, clock, notifier = _Repo(), _Gateway(), _Clock(), _Notifier()
        gateway.fail_finish = InstagramCallError(
            status_code=503, error_code="503", transient=True
        )
        run = _store(repo, _run())
        job = _job(repo, gateway, _Source(_snapshot()), clock, notifier)

        assert await job.tick() == 1
        assert repo.runs[run.run_id].publish_attempts == 1
        assert await job.tick() == 0

        clock.advance(60)
        assert await job.tick() == 1
        assert repo.runs[run.run_id].publish_attempts == 2
        clock.advance(300)
        assert await job.tick() == 1

        stored = repo.runs[run.run_id]
        assert stored.state is AutopilotRunState.PUBLISH_FAILED
        assert stored.publish_attempts == 3
        assert notifier.notices[0].outcome == NOTICE_PUBLISH_FAILED
        assert gateway.finishes == 3


@pytest.mark.unit
class TestAlreadyPosted:
    """Scenario: Post id already stored skips the Graph API."""

    async def test_no_graph_call(self) -> None:
        repo, gateway, notifier = _Repo(), _Gateway(), _Notifier()
        run = _store(
            repo,
            replace(
                _run(),
                ig_post_id="post-kept",
                ig_permalink="https://instagram.com/p/kept",
            ),
        )
        job = _job(repo, gateway, _Source(_snapshot()), _Clock(), notifier)

        await job.tick()

        assert gateway.opens == 0
        assert gateway.finishes == 0
        assert gateway.permalink_calls == 0
        stored = repo.runs[run.run_id]
        assert stored.state is AutopilotRunState.PUBLISHED
        assert stored.ig_permalink == "https://instagram.com/p/kept"
        assert notifier.notices[0].outcome == NOTICE_PUBLISHED


@pytest.mark.unit
class TestPublishBranches:
    """Edges around quota, token, age, and local pre-checks."""

    async def test_quota_zero_does_not_open_a_container(self) -> None:
        repo, gateway = _Repo(), _Gateway()
        gateway.quota = 0
        run = _store(repo, _run())
        job = _job(repo, gateway, _Source(_snapshot()), _Clock(), _Notifier())

        await job.tick()

        assert gateway.opens == 0
        assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISHING
        assert repo.runs[run.run_id].state_reason == REASON_QUOTA_EXHAUSTED

    async def test_missing_token_fails_immediately(self) -> None:
        """Scenario: No token is configured (tests/features/autopilot_ig_token.feature)."""
        repo, gateway = _Repo(), _Gateway()
        gateway.token = ""
        run = _store(repo, _run())
        job = _job(repo, gateway, _Source(_snapshot()), _Clock(), _Notifier())

        await job.tick()

        assert gateway.opens == 0
        assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISH_FAILED
        assert repo.runs[run.run_id].state_reason == REASON_IG_LOGIN_ABSENT
        assert repo.runs[run.run_id].publish_attempts == 0

    async def test_container_older_than_24h_is_recreated(self) -> None:
        repo, gateway = _Repo(), _Gateway()
        created = _NOW - timedelta(hours=24)
        _store(
            repo,
            replace(_run(), ig_container_id="old", ig_container_created_at=created),
        )
        job = _job(repo, gateway, _Source(_snapshot()), _Clock(), _Notifier())

        await job.tick()

        assert gateway.opens == 1

    async def test_container_younger_than_24h_is_reused(self) -> None:
        repo, gateway = _Repo(), _Gateway()
        created = _NOW - timedelta(hours=23)
        _store(
            repo,
            replace(_run(), ig_container_id="young", ig_container_created_at=created),
        )
        job = _job(repo, gateway, _Source(_snapshot()), _Clock(), _Notifier())

        await job.tick()

        assert gateway.opens == 0
        assert gateway.last_container == "young"

    async def test_missing_container_timestamp_creates_a_new_one(self) -> None:
        repo, gateway = _Repo(), _Gateway()
        _store(repo, replace(_run(), ig_container_id="untimed"))
        job = _job(repo, gateway, _Source(_snapshot()), _Clock(), _Notifier())

        await job.tick()

        assert gateway.opens == 1

    @pytest.mark.parametrize(
        ("snapshot", "reason"),
        [
            (None, REASON_CAROUSEL_MISSING),
            (replace(_snapshot(), is_public=False), REASON_CAROUSEL_NOT_PUBLIC),
            (
                replace(_snapshot(), workflow_status="draft"),
                ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH,
            ),
            (replace(_snapshot(), status="draft"), ERR_CAROUSEL_NOT_COMPLETED),
            (
                replace(_snapshot(), image_urls=("https://public.test/one.jpg",)),
                ERR_INSTAGRAM_IMAGE_COUNT_INVALID,
            ),
            (
                replace(_snapshot(), base_url_configured=False, image_urls=()),
                REASON_PUBLIC_BASE_URL_MISSING,
            ),
        ],
    )
    async def test_precheck_is_permanent(
        self,
        snapshot: CarouselPublishSnapshot | None,
        reason: str,
    ) -> None:
        repo, gateway, clock = _Repo(), _Gateway(), _Clock()
        run = _store(repo, _run())
        # Past the approve-release grace window (QA r2 R4c).
        clock.advance(RELEASE_GRACE_SECONDS + 1)
        job = _job(repo, gateway, _Source(snapshot), clock, _Notifier())

        await job.tick()

        assert gateway.opens == 0
        assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISH_FAILED
        assert repo.runs[run.run_id].state_reason == reason

    async def test_only_one_run_per_tick(self) -> None:
        repo, gateway = _Repo(), _Gateway()
        _store(repo, _run())
        second = _store(repo, _run())
        job = _job(repo, gateway, _Source(_snapshot()), _Clock(), _Notifier())

        assert await job.tick() == 1

        assert gateway.opens == 1
        assert repo.runs[second.run_id].state is AutopilotRunState.PUBLISHING

    async def test_permalink_failure_still_publishes(self) -> None:
        repo, gateway = _Repo(), _Gateway()
        gateway.fail_permalink = True
        run = _store(repo, _run())
        job = _job(repo, gateway, _Source(_snapshot()), _Clock(), _Notifier())

        await job.tick()

        stored = repo.runs[run.run_id]
        assert stored.state is AutopilotRunState.PUBLISHED
        assert stored.ig_post_id == "post-1"
        assert stored.ig_permalink is None

    async def test_exhausted_attempts_do_not_call_graph(self) -> None:
        repo, gateway = _Repo(), _Gateway()
        run = _store(repo, replace(_run(), publish_attempts=3, state_reason="503"))
        job = _job(repo, gateway, _Source(_snapshot()), _Clock(), _Notifier())

        await job.tick()

        assert gateway.opens == 0
        assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISH_FAILED
        assert repo.runs[run.run_id].state_reason == "503"


@pytest.mark.unit
class TestManualPublish:
    """Scenario: Manual route does not publish twice."""

    async def test_stored_post_id_skips_the_publisher(self) -> None:
        repo, gateway = _Repo(), _Gateway()
        _store(repo, replace(_run(), ig_post_id="post-kept"))
        manual = _manual(repo, gateway, _Source(_snapshot()))

        outcome = await manual.publish(
            ManualPublishCommand(project_id=_PROJECT, caption="cap", image_urls=_SEVEN)
        )

        assert outcome.status == "published"
        assert outcome.ig_post_id == "post-kept"
        assert gateway.atomics == 0
        assert gateway.opens == 0

    async def test_atomic_publisher_is_used_when_resume_is_unavailable(self) -> None:
        repo, gateway = _Repo(), _Gateway()
        gateway.resume = False
        manual = _manual(repo, gateway, _Source(None))

        outcome = await manual.publish(
            ManualPublishCommand(project_id=_PROJECT, caption="cap", image_urls=_SEVEN)
        )

        assert gateway.atomics == 1
        assert outcome.ig_post_id == "atomic-post"
        assert repo.runs == {}

    async def test_exhausted_reason_defaults_when_blank(self) -> None:
        repo, gateway = _Repo(), _Gateway()
        run = _store(repo, replace(_run(), publish_attempts=3))
        job = _job(repo, gateway, _Source(_snapshot()), _Clock(), _Notifier())

        await job.tick()

        assert repo.runs[run.run_id].state_reason == REASON_ATTEMPTS_EXHAUSTED
