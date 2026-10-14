"""Story step after a carousel publish (AE-0369).

Gherkin: tests/features/autopilot_story_and_music.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import timedelta

import pytest

from rag_backend.modules.autopilot.application.manual_publish import (
    ManualInstagramPublish,
)
from rag_backend.modules.autopilot.application.publish_job import (
    InstagramPublishJob,
    PublishJobDependencies,
)
from rag_backend.modules.autopilot.application.story_step import (
    InstagramStoryStep,
    StoryDependencies,
    post_extras,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.publish import (
    ManualPublishCommand,
    StoredContainer,
)
from rag_backend.modules.autopilot.domain.story import (
    SaveStoryContainer,
    SaveStoryResult,
    StoryMedia,
    StoryRecord,
)
from rag_backend.modules.autopilot.story_constants import (
    MUSIC_DEFAULT,
    REASON_STORY_CAROUSEL_MISSING,
    REASON_STORY_IMAGE_MISSING,
    REASON_STORY_UNEXPECTED,
    STORY_STATE_FAILED,
    STORY_STATE_PUBLISHED,
)
from tests.unit.modules.autopilot.test_instagram_publish_job import (
    _NOW,
    _PROJECT,
    _SEVEN,
    _Claims,
    _Clock,
    _Gateway,
    _Notifier,
    _Repo,
    _run,
    _snapshot,
    _Source,
)

_IMAGE = "https://public.test/api/carousels/carousel-1/story-image/pt.jpg"
_SYNTHWAVE = "lo-fi eletrônico / synthwave"


def _transient() -> InstagramCallError:
    return InstagramCallError(status_code=503, error_code="503", transient=True)


def _permanent() -> InstagramCallError:
    return InstagramCallError(status_code=400, error_code="36003", transient=False)


@dataclass
class _StoryStore:
    records: dict[str, StoryRecord] = field(default_factory=dict)
    containers: list[SaveStoryContainer] = field(default_factory=list)

    async def get(self, project_id: str) -> StoryRecord | None:
        return self.records.get(project_id)

    async def save_container(self, command: SaveStoryContainer) -> None:
        self.containers.append(command)
        self.records[command.project_id] = StoryRecord(
            project_id=command.project_id,
            state="pending",
            container=command.container,
            media_id=None,
            error=None,
        )

    async def save_result(self, command: SaveStoryResult) -> None:
        prior = self.records.get(command.project_id)
        self.records[command.project_id] = StoryRecord(
            project_id=command.project_id,
            state=command.state,
            container=prior.container if prior is not None else None,
            media_id=command.media_id,
            error=command.error,
        )


@dataclass
class _StoryMedia:
    media: StoryMedia | None = field(
        default_factory=lambda: StoryMedia(
            image_url=_IMAGE, niche="AI", image_style="neo_anime"
        )
    )
    crash: bool = False

    async def load(self, project_id: str) -> StoryMedia | None:
        del project_id
        if self.crash:
            raise RuntimeError("render crashed")
        return self.media


@dataclass
class _StoryGateway:
    opens: int = 0
    publishes: int = 0
    finished: list[str] = field(default_factory=list)
    open_errors: list[InstagramCallError] = field(default_factory=list)
    finish_errors: list[InstagramCallError] = field(default_factory=list)
    already_published: bool = False
    status_reads: int = 0

    async def open_story(self, image_url: str) -> str:
        assert image_url == _IMAGE
        self.opens += 1
        if self.open_errors:
            raise self.open_errors.pop(0)
        return f"story-container-{self.opens}"

    async def was_published(self, container: StoredContainer) -> bool:
        del container
        self.status_reads += 1
        return self.already_published

    async def finish_story(self, container: StoredContainer) -> str | None:
        self.finished.append(container.container_id)
        if self.finish_errors:
            raise self.finish_errors.pop(0)
        if self.already_published:
            return None
        self.publishes += 1
        return "story-media-1"


@dataclass
class _Checkpoint:
    commits: int = 0

    async def commit(self) -> None:
        self.commits += 1


@dataclass
class _StoryKit:
    store: _StoryStore = field(default_factory=_StoryStore)
    media: _StoryMedia = field(default_factory=_StoryMedia)
    gateway: _StoryGateway = field(default_factory=_StoryGateway)
    checkpoint: _Checkpoint = field(default_factory=_Checkpoint)
    clock: _Clock = field(default_factory=_Clock)

    def step(self) -> InstagramStoryStep:
        return InstagramStoryStep(
            StoryDependencies(
                store=self.store,
                media=self.media,
                gateway=self.gateway,
                checkpoint=self.checkpoint,
                clock=self.clock,
            )
        )


def _job_deps(
    repo: _Repo, kit: _StoryKit, notifier: _Notifier
) -> PublishJobDependencies:
    return PublishJobDependencies(
        runs=repo,
        source=_Source(_snapshot()),
        gateway=_Gateway(),
        notifier=notifier,
        clock=_Clock(),
        checkpoint=repo,
        claims=_Claims(),
        story=kit.step(),
    )


@pytest.mark.unit
class TestPublishedCarouselPostsOneStory:
    """Scenario: A published carousel also posts one Story."""

    async def test_story_published_and_notice_says_so(self) -> None:
        repo, kit, notifier = _Repo(), _StoryKit(), _Notifier()
        run = _run()
        repo.runs[run.run_id] = run

        assert await InstagramPublishJob(_job_deps(repo, kit, notifier)).tick() == 1

        assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISHED
        record = kit.store.records[_PROJECT]
        assert record.state == STORY_STATE_PUBLISHED
        assert record.media_id == "story-media-1"
        extras = notifier.notices[0].extras
        assert extras is not None
        assert extras.story_status == "published"
        assert extras.story_error is None
        assert extras.music_style == _SYNTHWAVE

    async def test_container_is_committed_before_media_publish(self) -> None:
        kit = _StoryKit()
        await kit.step().run(_PROJECT)
        assert kit.store.containers[0].container.container_id == "story-container-1"
        assert kit.store.containers[0].container.created_at == _NOW
        # One commit for the container, one for the result.
        assert kit.checkpoint.commits == 2


@pytest.mark.unit
class TestDoubleTickPostsOneStory:
    """Scenario: A double tick posts one Story."""

    async def test_two_ticks_one_story(self) -> None:
        repo, kit = _Repo(), _StoryKit()
        run = _run()
        repo.runs[run.run_id] = run
        job = InstagramPublishJob(_job_deps(repo, kit, _Notifier()))

        assert await job.tick() == 1
        assert await job.tick() == 0

        assert kit.gateway.publishes == 1

    async def test_rerun_after_a_crash_before_the_transition(self) -> None:
        """The run is still publishing with a post id; the Story is not reposted."""
        repo, kit, notifier = _Repo(), _StoryKit(), _Notifier()
        await kit.step().run(_PROJECT)
        run = replace(_run(), ig_post_id="post-1")
        repo.runs[run.run_id] = run

        await InstagramPublishJob(_job_deps(repo, kit, notifier)).tick()

        assert kit.gateway.publishes == 1
        assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISHED
        extras = notifier.notices[0].extras
        assert extras is not None and extras.story_status == "published"


@pytest.mark.unit
class TestStoredStoryShortCircuits:
    """Scenario: A stored Story id short-circuits the Story step."""

    async def test_no_graph_call(self) -> None:
        kit = _StoryKit()
        kit.store.records[_PROJECT] = StoryRecord(
            project_id=_PROJECT,
            state=STORY_STATE_PUBLISHED,
            container=None,
            media_id="story-media-0",
            error=None,
        )

        extras = await kit.step().run(_PROJECT)

        assert extras.story_status == "published"
        assert kit.gateway.opens == 0
        assert kit.gateway.finished == []


@pytest.mark.unit
class TestCrashAfterStoryContainer:
    """Scenario: A crash after the Story container is resumed, not recreated."""

    async def test_fresh_container_is_resumed(self) -> None:
        kit = _StoryKit()
        kit.store.records[_PROJECT] = StoryRecord(
            project_id=_PROJECT,
            state="pending",
            container=StoredContainer(
                container_id="story-kept", created_at=_NOW - timedelta(hours=1)
            ),
            media_id=None,
            error=None,
        )

        extras = await kit.step().run(_PROJECT)

        assert extras.story_status == "published"
        assert kit.gateway.opens == 0
        assert kit.gateway.finished == ["story-kept"]

    async def test_expired_published_container_is_not_reposted(self) -> None:
        kit = _StoryKit()
        kit.gateway.already_published = True
        kit.store.records[_PROJECT] = StoryRecord(
            project_id=_PROJECT,
            state="pending",
            container=StoredContainer(
                container_id="story-old", created_at=_NOW - timedelta(hours=30)
            ),
            media_id=None,
            error=None,
        )

        extras = await kit.step().run(_PROJECT)

        assert extras.story_status == "published"
        assert kit.gateway.opens == 0
        assert kit.gateway.publishes == 0
        assert kit.store.records[_PROJECT].state == STORY_STATE_PUBLISHED

    async def test_expired_unpublished_container_is_replaced(self) -> None:
        kit = _StoryKit()
        kit.store.records[_PROJECT] = StoryRecord(
            project_id=_PROJECT,
            state="failed",
            container=StoredContainer(
                container_id="story-old", created_at=_NOW - timedelta(hours=30)
            ),
            media_id=None,
            error="503",
        )

        await kit.step().run(_PROJECT)

        assert kit.gateway.status_reads == 1
        assert kit.gateway.finished == ["story-container-1"]


@pytest.mark.unit
class TestTransientStoryErrorRetried:
    """Scenario: A transient Story error is retried up to 3 times."""

    async def test_third_attempt_publishes(self) -> None:
        kit = _StoryKit()
        kit.gateway.open_errors = [_transient(), _transient()]

        extras = await kit.step().run(_PROJECT)

        assert extras.story_status == "published"
        assert kit.gateway.opens == 3
        assert kit.gateway.publishes == 1

    async def test_three_transient_errors_fail(self) -> None:
        kit = _StoryKit()
        kit.gateway.open_errors = [_transient(), _transient(), _transient()]

        extras = await kit.step().run(_PROJECT)

        assert extras.story_status == "failed"
        assert extras.story_error == "503"
        assert kit.gateway.opens == 3

    async def test_retry_resumes_the_container_it_stored(self) -> None:
        kit = _StoryKit()
        kit.gateway.finish_errors = [_transient()]

        extras = await kit.step().run(_PROJECT)

        assert extras.story_status == "published"
        assert kit.gateway.opens == 1
        assert kit.gateway.finished == ["story-container-1", "story-container-1"]


@pytest.mark.unit
class TestStoryFailureLeavesPostPublished:
    """Scenario: A Story failure leaves the post published."""

    async def test_permanent_error_is_recorded_and_notified(self) -> None:
        repo, kit, notifier = _Repo(), _StoryKit(), _Notifier()
        kit.gateway.open_errors = [_permanent()]
        run = _run()
        repo.runs[run.run_id] = run

        await InstagramPublishJob(_job_deps(repo, kit, notifier)).tick()

        assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISHED
        assert kit.gateway.opens == 1
        record = kit.store.records[_PROJECT]
        assert record.state == STORY_STATE_FAILED
        assert record.error == "36003"
        extras = notifier.notices[0].extras
        assert extras is not None
        assert extras.story_status == "failed"
        assert extras.story_error == "36003"

    async def test_unexpected_error_never_raises(self) -> None:
        kit = _StoryKit()
        kit.media.crash = True

        extras = await kit.step().run(_PROJECT)

        assert extras.story_status == "failed"
        assert extras.story_error == REASON_STORY_UNEXPECTED
        assert extras.music_style == MUSIC_DEFAULT


@pytest.mark.unit
class TestMissingStoryImage:
    """Scenario: No slide 1 means no Story image."""

    async def test_missing_image_is_recorded(self) -> None:
        kit = _StoryKit()
        kit.media.media = StoryMedia(image_url=None, niche="AI", image_style="x")

        extras = await kit.step().run(_PROJECT)

        assert extras.story_error == REASON_STORY_IMAGE_MISSING
        assert extras.music_style == _SYNTHWAVE
        assert kit.store.records[_PROJECT].error == REASON_STORY_IMAGE_MISSING
        assert kit.gateway.opens == 0

    async def test_missing_carousel_is_recorded(self) -> None:
        kit = _StoryKit()
        kit.media.media = None

        extras = await kit.step().run(_PROJECT)

        assert extras.story_error == REASON_STORY_CAROUSEL_MISSING
        assert extras.music_style == MUSIC_DEFAULT


@pytest.mark.unit
class TestNoStoryPublisher:
    """Scenario: A publisher that cannot post Stories skips the Story step."""

    async def test_no_runner_means_no_extras(self) -> None:
        assert await post_extras(None, _PROJECT) is None

    async def test_no_project_means_no_extras(self) -> None:
        assert await post_extras(_StoryKit().step(), None) is None

    async def test_publish_job_without_story_sends_no_story_line(self) -> None:
        repo, notifier = _Repo(), _Notifier()
        run = _run()
        repo.runs[run.run_id] = run
        deps = PublishJobDependencies(
            runs=repo,
            source=_Source(_snapshot()),
            gateway=_Gateway(),
            notifier=notifier,
            clock=_Clock(),
            checkpoint=repo,
            claims=_Claims(),
        )

        await InstagramPublishJob(deps).tick()

        assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISHED
        assert notifier.notices[0].extras is None


@pytest.mark.unit
class TestManualPublishPostsOneStory:
    """Scenario: The manual publish route also posts the Story once."""

    async def test_twice_without_a_run(self) -> None:
        repo, kit = _Repo(), _StoryKit()
        claims = _Claims()
        deps = PublishJobDependencies(
            runs=repo,
            source=_Source(_snapshot()),
            gateway=_Gateway(),
            notifier=_Notifier(),
            clock=_Clock(),
            checkpoint=repo,
            claims=claims,
            story=kit.step(),
        )
        manual = ManualInstagramPublish(deps)
        command = ManualPublishCommand(
            project_id=_PROJECT, caption="caption", image_urls=_SEVEN
        )

        first = await manual.publish(command)
        second = await manual.publish(command)

        assert first.ig_post_id == second.ig_post_id == "post-1"
        assert kit.gateway.publishes == 1
        assert kit.store.records[_PROJECT].state == STORY_STATE_PUBLISHED
        assert claims.manual[_PROJECT].ig_post_id == "post-1"
