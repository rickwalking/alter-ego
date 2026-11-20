"""The repost worker tick: render, notify, expire, publish, poll.

Gherkin: tests/features/autopilot_repost_publish_ae0629.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from rag_backend.modules.autopilot.application.repost_tick import (
    RepostTick,
    RepostTickDeps,
)
from rag_backend.modules.autopilot.application.repost_tick_ports import (
    ContainerRequest,
    ContainerState,
    PromptDelivery,
    RenderedFiles,
    RepostRenderError,
    StudioJob,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.domain.repost import Repost
from rag_backend.modules.autopilot.domain.repost_ports import StatusChange
from rag_backend.modules.autopilot.repost_constants import (
    STATUS_APPROVED,
    STATUS_EXPIRED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_PROCESSING,
    STATUS_PUBLISHED,
)
from tests.unit.modules.autopilot.repost_fakes import (
    MEDIA,
    NOW,
    Clock,
    FakeReels,
    MemoryStore,
    reel,
    stored,
)


@dataclass
class _Studio:
    root: Path
    fail: str | None = None
    fits: bool = True
    jobs: list[StudioJob] = field(default_factory=list)
    files: set[str] = field(
        default_factory=lambda: {"preview.mp4", "cover.jpg", "original_cover.jpg"}
    )

    async def prepare(self, job: StudioJob) -> RenderedFiles:
        self.jobs.append(job)
        if self.fail is not None:
            raise RepostRenderError(self.fail)
        return RenderedFiles(
            preview=self.root / "preview.mp4",
            cover=self.root / "cover.jpg",
            original_cover=self.root / "original_cover.jpg",
            fits_telegram=self.fits,
            source_size=(360, 640),
        )

    def public_url(self, repost: Repost, file_name: str) -> str:
        return f"https://site/r/{repost.id}/{file_name}"

    def existing(self, repost: Repost, file_name: str) -> Path | None:
        del repost
        return self.root / file_name if file_name in self.files else None


@dataclass
class _Prompts:
    message_id: int | None = 55
    delivered: list[PromptDelivery] = field(default_factory=list)
    edits: list[tuple[int, str]] = field(default_factory=list)
    tells: list[str] = field(default_factory=list)

    async def deliver(self, delivery: PromptDelivery) -> int | None:
        self.delivered.append(delivery)
        return self.message_id

    async def edit(self, message_id: int, text: str) -> None:
        self.edits.append((message_id, text))

    async def tell(self, text: str) -> None:
        self.tells.append(text)


@dataclass
class _Publisher:
    state: ContainerState = field(
        default_factory=lambda: ContainerState(code="IN_PROGRESS", detail=None)
    )
    create_error: InstagramCallError | None = None
    status_error: InstagramCallError | None = None
    publish_error: InstagramCallError | None = None
    permalink_error: InstagramCallError | None = None
    created: list[ContainerRequest] = field(default_factory=list)
    published: list[str] = field(default_factory=list)

    async def create(self, request: ContainerRequest) -> str:
        if self.create_error is not None:
            raise self.create_error
        self.created.append(request)
        return "c-1"

    async def status(self, container_id: str) -> ContainerState:
        del container_id
        if self.status_error is not None:
            raise self.status_error
        return self.state

    async def publish(self, container_id: str) -> str:
        if self.publish_error is not None:
            raise self.publish_error
        self.published.append(container_id)
        return "new-1"

    async def permalink(self, media_id: str) -> str | None:
        if self.permalink_error is not None:
            raise self.permalink_error
        return f"https://www.instagram.com/reel/{media_id}/"


@dataclass
class _Metrics:
    async def metrics(self, media_id: str) -> InsightMetrics:
        del media_id
        return InsightMetrics(views=10)


@dataclass
class _World:
    store: MemoryStore
    studio: _Studio
    prompts: _Prompts
    publisher: _Publisher
    reels: FakeReels
    clock: Clock

    def tick(
        self, *, with_publisher: bool = True, with_reels: bool = True
    ) -> RepostTick:
        return RepostTick(
            RepostTickDeps(
                store=self.store,
                studio=self.studio,
                prompts=self.prompts,
                metrics=_Metrics(),
                clock=self.clock,
                reels=self.reels if with_reels else None,
                publisher=self.publisher if with_publisher else None,
            )
        )


def _world(tmp_path: Path, *rows: Repost) -> _World:
    store = MemoryStore()
    for row in rows:
        store.rows[row.id] = row
    return _World(
        store=store,
        studio=_Studio(root=tmp_path),
        prompts=_Prompts(),
        publisher=_Publisher(),
        reels=FakeReels(items={MEDIA: reel()}),
        clock=Clock(),
    )


def _err(transient: bool) -> InstagramCallError:
    return InstagramCallError(
        status_code=500 if transient else 400, error_code="graph_x", transient=transient
    )


# Scenario: A pending draft is rendered and sent to the owner
async def test_pending_draft_is_rendered_and_sent(tmp_path: Path) -> None:
    draft = stored()
    world = _world(tmp_path, draft)
    assert await world.tick().run() == 1
    saved = world.store.rows[draft.id]
    assert saved.preview_ready_at == NOW and saved.telegram_message_id == 55
    delivery = world.prompts.delivered[0]
    assert delivery.notice.metrics.views == 10 and delivery.notice.preview_link is None
    assert delivery.notice.source_size == (360, 640)
    assert world.studio.jobs[0].reel.video_url


# Scenario: A preview too large for Telegram is sent as a link
async def test_big_preview_is_a_link(tmp_path: Path) -> None:
    draft = stored()
    world = _world(tmp_path, draft)
    world.studio.fits = False
    await world.tick().run()
    assert (
        world.prompts.delivered[0].notice.preview_link
        == f"https://site/r/{draft.id}/preview.mp4"
    )


async def test_prompt_not_accepted_keeps_no_message_id(tmp_path: Path) -> None:
    draft = stored()
    world = _world(tmp_path, draft)
    world.prompts.message_id = None
    await world.tick().run()
    assert world.store.rows[draft.id].telegram_message_id is None
    assert world.store.rows[draft.id].preview_ready_at == NOW


async def test_one_render_per_tick(tmp_path: Path) -> None:
    rows = [stored(created_at=NOW - timedelta(minutes=i)) for i in range(2)]
    world = _world(tmp_path, *rows)
    assert await world.tick().run() == 1


# Scenario: A failed render ends the draft without messaging the owner
async def test_render_failure_fails_silently(tmp_path: Path) -> None:
    draft = stored()
    world = _world(tmp_path, draft)
    world.studio.fail = "render_failed"
    await world.tick().run()
    saved = world.store.rows[draft.id]
    assert (saved.status, saved.error_code) == (STATUS_FAILED, "render_failed")
    assert saved.error_message == "ffmpeg could not render the preview."
    assert world.prompts.delivered == [] and world.prompts.tells == []


async def test_missing_source_fails_the_render(tmp_path: Path) -> None:
    for reels in (FakeReels(), FakeReels(fail=_err(True))):
        draft = stored()
        world = _world(tmp_path, draft)
        world.reels = reels
        await world.tick().run()
        assert world.store.rows[draft.id].error_code == "source_unavailable"
    draft = stored()
    world = _world(tmp_path, draft)
    await world.tick(with_reels=False).run()
    assert world.store.rows[draft.id].error_code == "source_unavailable"


# Scenario: An unanswered draft expires after 12 hours
async def test_expiry_edits_the_prompt(tmp_path: Path) -> None:
    draft = stored(preview_ready_at=NOW, telegram_message_id=7)
    world = _world(tmp_path, draft)
    world.clock.at = NOW + timedelta(hours=12)
    assert await world.tick().run() == 1
    assert world.store.rows[draft.id].status == STATUS_EXPIRED
    assert world.prompts.edits[0][0] == 7
    silent = stored(preview_ready_at=NOW)
    world = _world(tmp_path, silent)
    world.clock.at = NOW + timedelta(hours=13)
    await world.tick().run()
    assert world.prompts.edits == []


# Scenario: An approved draft publishes only once publish_at has passed
async def test_approved_waits_for_publish_at(tmp_path: Path) -> None:
    draft = stored(
        status=STATUS_APPROVED,
        cover_choice="grok",
        publish_at=NOW + timedelta(hours=1),
        collaborators=("rick",),
    )
    world = _world(tmp_path, draft)
    assert await world.tick().run() == 0
    world.clock.at = NOW + timedelta(hours=1)
    assert await world.tick().run() == 1
    request = world.publisher.created[0]
    assert request.video_url.endswith("/preview.mp4")
    assert request.cover_url is not None and request.cover_url.endswith("/cover.jpg")
    assert (request.caption, request.share_to_feed, request.collaborators) == (
        draft.caption,
        True,
        ("rick",),
    )
    saved = world.store.rows[draft.id]
    assert (saved.status, saved.container_id) == (STATUS_PROCESSING, "c-1")


# Scenario: The original cover is used when the owner chose it
async def test_original_cover_choice(tmp_path: Path) -> None:
    draft = stored(status=STATUS_APPROVED, cover_choice="original", publish_at=NOW)
    world = _world(tmp_path, draft)
    await world.tick().run()
    cover = world.publisher.created[0].cover_url
    assert cover is not None and cover.endswith("/original_cover.jpg")
    draft2 = stored(status=STATUS_APPROVED, cover_choice="original", publish_at=NOW)
    world2 = _world(tmp_path, draft2)
    world2.studio.files = {"preview.mp4"}
    await world2.tick().run()
    assert world2.publisher.created[0].cover_url is None


# Scenario: A transient Graph error is retried on the next tick
async def test_transient_create_error_stays_approved(tmp_path: Path) -> None:
    draft = stored(status=STATUS_APPROVED, publish_at=NOW)
    world = _world(tmp_path, draft)
    world.publisher.create_error = _err(True)
    assert await world.tick().run() == 0
    assert world.store.rows[draft.id].status == STATUS_APPROVED


async def test_permanent_create_error_fails_and_tells(tmp_path: Path) -> None:
    draft = stored(status=STATUS_APPROVED, publish_at=NOW)
    world = _world(tmp_path, draft)
    world.publisher.create_error = _err(False)
    await world.tick().run()
    assert world.store.rows[draft.id].error_code == "graph_x"
    assert "graph_x" in world.prompts.tells[0]


async def test_no_publisher_does_nothing(tmp_path: Path) -> None:
    rows = (
        stored(status=STATUS_APPROVED, publish_at=NOW),
        stored(status=STATUS_PROCESSING, container_id="c"),
    )
    world = _world(tmp_path, *rows)
    assert await world.tick(with_publisher=False).run() == 0


def _processing(**changes: object) -> Repost:
    return stored(
        status=STATUS_PROCESSING,
        container_id="c-9",
        container_created_at=NOW,
        **changes,
    )


# Scenario: A finished container is published
async def test_finished_container_is_published(tmp_path: Path) -> None:
    draft = _processing()
    world = _world(tmp_path, draft)
    world.publisher.state = ContainerState(code="FINISHED", detail=None)
    assert await world.tick().run() == 1
    saved = world.store.rows[draft.id]
    assert (saved.status, saved.new_media_id, saved.published_at) == (
        STATUS_PUBLISHED,
        "new-1",
        NOW,
    )
    assert saved.new_permalink == "https://www.instagram.com/reel/new-1/"
    assert "reel/new-1" in world.prompts.tells[0]


async def test_permalink_failure_still_publishes(tmp_path: Path) -> None:
    draft = _processing()
    world = _world(tmp_path, draft)
    world.publisher.state = ContainerState(code="PUBLISHED", detail=None)
    world.publisher.permalink_error = _err(True)
    await world.tick().run()
    saved = world.store.rows[draft.id]
    assert (saved.status, saved.new_permalink) == (STATUS_PUBLISHED, None)
    assert "new-1" in world.prompts.tells[0]


async def test_publish_error_fails(tmp_path: Path) -> None:
    draft = _processing()
    world = _world(tmp_path, draft)
    world.publisher.state = ContainerState(code="FINISHED", detail=None)
    world.publisher.publish_error = _err(False)
    await world.tick().run()
    assert world.store.rows[draft.id].status == STATUS_FAILED


# Scenario: A container error or timeout fails the draft
async def test_container_error_and_timeout(tmp_path: Path) -> None:
    draft = _processing()
    world = _world(tmp_path, draft)
    world.publisher.state = ContainerState(code="ERROR", detail="bad video")
    await world.tick().run()
    saved = world.store.rows[draft.id]
    assert (saved.error_code, saved.error_message) == ("container_error", "bad video")
    slow = _processing()
    world = _world(tmp_path, slow)
    assert await world.tick().run() == 0
    world.clock.at = NOW + timedelta(minutes=30)
    assert await world.tick().run() == 0
    assert world.store.rows[slow.id].status == STATUS_PROCESSING
    world.clock.at = NOW + timedelta(minutes=30, seconds=1)
    await world.tick().run()
    assert world.store.rows[slow.id].error_code == "container_timeout"


async def test_poll_errors(tmp_path: Path) -> None:
    draft = _processing()
    world = _world(tmp_path, draft)
    world.publisher.status_error = _err(True)
    assert await world.tick().run() == 0
    world.publisher.status_error = _err(False)
    await world.tick().run()
    assert world.store.rows[draft.id].status == STATUS_FAILED


async def test_lost_race_moves_nothing(tmp_path: Path) -> None:
    class _Racing(MemoryStore):
        async def save(self, change: StatusChange) -> bool:
            return False

    rows = (
        stored(),
        stored(preview_ready_at=NOW, expires_at=NOW - timedelta(hours=1)),
        stored(status=STATUS_APPROVED, publish_at=NOW),
    )
    world = _world(tmp_path)
    world.store = _Racing(rows={r.id: r for r in rows})
    assert await world.tick().run() == 0
    assert world.prompts.delivered == []
    fin = _processing()
    world = _world(tmp_path)
    world.store = _Racing(rows={fin.id: fin})
    world.publisher.state = ContainerState(code="FINISHED", detail=None)
    assert await world.tick().run() == 0
    failing = stored()
    world = _world(tmp_path)
    world.store = _Racing(rows={failing.id: failing})
    world.studio.fail = "render_failed"
    assert await world.tick().run() == 0


async def test_processing_without_container_is_skipped(tmp_path: Path) -> None:
    world = _world(tmp_path, stored(status=STATUS_PROCESSING))
    assert await world.tick().run() == 0
    other = stored(status=STATUS_PENDING, preview_ready_at=NOW)
    world = _world(tmp_path)
    world.store.rows[other.id] = other
    assert await world.tick().run() == 0
