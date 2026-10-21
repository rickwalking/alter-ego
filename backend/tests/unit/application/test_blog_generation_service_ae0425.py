"""The blog generation run end to end with fakes (AE-0425).

Feature: backend/tests/features/blog_generate_ae0425.feature
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from rag_backend.application.services import blog_workflow_observability
from rag_backend.application.services.blog import (
    blog_generation_service as service_module,
)
from rag_backend.application.services.blog import blog_image_batch as image_module
from rag_backend.application.services.blog.blog_generated_document import (
    ImageTitles,
)
from rag_backend.application.services.blog.blog_generation_service import (
    BlogGenerationDeps,
    BlogGenerationService,
    GenerationJob,
    GenerationTimings,
)
from rag_backend.application.services.blog.blog_quality_gate import (
    BlogQualityGate,
    QualityGateDeps,
)
from rag_backend.application.services.blog_workflow_observability import (
    BlogPhaseScope,
)
from rag_backend.domain.constants.blog_editor import PHASE_BLOG_SECTION_IMAGE
from rag_backend.domain.constants.blog_generation import (
    ERR_GENERATION_CANCELLED,
    ERR_GENERATION_CONFLICT,
    ERR_GENERATION_FAILED,
    ERR_GENERATION_LLM_FAILED,
    ERR_GENERATION_TIMEOUT,
    ERR_SECTION_COUNT_MISMATCH,
    GENERATION_STATUS_COMPLETE,
    GENERATION_STATUS_FAILED,
    GENERATION_STATUS_PARTIAL,
    PHASE_BLOG_GENERATION,
)
from rag_backend.domain.models.blog_document import BlogImage, parse_blog_content
from rag_backend.domain.models.blog_generation import (
    DocumentApply,
    DraftArticle,
    DraftSection,
    GenerationLease,
    GenerationTrace,
    WriterBrief,
)
from tests.blog_generation_fakes import (
    FAIL_IMAGE_MARKER,
    FakeImageGenerator,
    FakeScorer,
    FakeStore,
    FakeWriter,
    article,
    brief,
    english_gate,
    english_sections,
    image_batch,
    sections,
    writer_failure,
)

POST_ID = "22222222-2222-4222-8222-222222222222"


@pytest.fixture(autouse=True)
def _no_langfuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate from any Langfuse client an earlier test configured (its flush
    to an unreachable host would eat the run's timeout)."""
    from contextlib import nullcontext

    from rag_backend.application.services.blog import (
        blog_generation_service,
        blog_image_batch,
    )

    for module in (blog_generation_service, blog_image_batch):
        monkeypatch.setattr(
            module,
            "blog_phase_trace",
            lambda _scope, **_kwargs: nullcontext(MagicMock()),
        )
    # The editor's single-image service (AE-0424) traces with its own helper.
    from rag_backend.application.services.blog import blog_image_service as _single

    monkeypatch.setattr(_single, "blog_ai_propagate", lambda *_a: nullcontext())


def _service(
    tmp: Path,
    writer: FakeWriter,
    store: FakeStore,
    timeout: float = 5.0,
) -> BlogGenerationService:
    images = image_batch(tmp, FakeImageGenerator())
    gate = BlogQualityGate(
        QualityGateDeps(writer=writer, scorer=FakeScorer(scores=[82.0]))
    )
    return BlogGenerationService(
        BlogGenerationDeps(
            writer=writer,
            gate=gate,
            english=english_gate(gate),
            images=images,
            store=store,
            timings=GenerationTimings(
                text_timeout_seconds=timeout,
                image_wave_seconds=timeout,
                heartbeat_seconds=0.01,
            ),
        )
    )


def _job(count: int = 4, retitle: bool = False) -> GenerationJob:
    return GenerationJob(
        lease=GenerationLease(post_id=POST_ID, lease_id="lease-a", lock_version=1),
        brief=brief(count),
        trace=GenerationTrace(
            project_id="carousel-1", user_id="user-1", post_id=POST_ID
        ),
        retitle=retitle,
    )


def _final(store: FakeStore) -> dict[str, object]:
    return store.contents[-1]


async def test_a_complete_run_stores_a_scored_document_with_images(
    tmp_path: Path,
) -> None:
    # Scenario: A cover and one image slot per section are created
    store = FakeStore()
    outcome = await _service(tmp_path, FakeWriter(), store).run(_job(4))
    assert outcome is not None
    assert outcome.status == GENERATION_STATUS_COMPLETE
    assert outcome.image_count == 5
    assert len(store.contents) == 2
    document = parse_blog_content(_final(store))
    assert len(document.sections) == 4
    assert document.cover is not None
    assert all(section.image is not None for section in document.sections)
    # Scenario: The voice score is mirrored for the listing badge
    assert document.quality is not None
    assert document.quality.voice_score == 82.0
    assert store.applied[0].voice_score == 82.0  # the article write
    assert store.generated == 5  # reserved on the per-post cap before the spend
    # EN translation: same ids, own quality, own alt text.
    english = document.translations["en"]
    assert [s.id for s in english.sections] == [s.id for s in document.sections]
    assert english.quality is not None
    assert english.sections[1].image is not None
    assert english.sections[1].image.alt == "Section 2"
    assert outcome.title is None
    assert store.outcomes == [outcome]


async def test_section_and_slot_count_follow_the_slide_count(tmp_path: Path) -> None:
    # Scenario: Section and image count follow the carousel slide count
    writer = FakeWriter(draft_article=article(9))
    store = FakeStore()
    outcome = await _service(tmp_path, writer, store).run(_job(9))
    document = parse_blog_content(_final(store))
    assert len(document.sections) == 9
    assert outcome is not None
    assert outcome.image_count == 10


async def test_a_failed_image_makes_the_run_partial(tmp_path: Path) -> None:
    # Scenario: A failed image leaves the slot empty and does not fail the draft
    pt = list(sections(4))
    pt[2] = DraftSection(heading=FAIL_IMAGE_MARKER, body_md=pt[2].body_md)
    draft = DraftArticle("T", tuple(pt), "T", english_sections(4))
    store = FakeStore()
    outcome = await _service(tmp_path, FakeWriter(draft_article=draft), store).run(
        _job(4)
    )
    assert outcome is not None
    assert outcome.status == GENERATION_STATUS_PARTIAL
    document = parse_blog_content(_final(store))
    failed = document.sections[2]
    assert failed.image is None
    assert outcome.errors[0]["slot"] == failed.id
    assert outcome.recoverable is True
    assert document.sections[0].body_md


async def test_an_llm_failure_fails_without_storing_content(tmp_path: Path) -> None:
    # Scenario: An LLM failure leaves the draft with status failed
    store = FakeStore()
    writer = FakeWriter(draft_error=writer_failure())
    outcome = await _service(tmp_path, writer, store).run(_job())
    assert outcome is not None
    assert outcome.status == GENERATION_STATUS_FAILED
    assert outcome.errors[0]["code"] == ERR_GENERATION_LLM_FAILED
    assert outcome.recoverable is True
    assert store.contents == []


async def test_a_count_mismatch_is_never_stored(tmp_path: Path) -> None:
    # Scenario: A writer section-count mismatch is not silently stored
    seven = DraftArticle("T", sections(7), "T", english_sections(7))
    store = FakeStore()
    outcome = await _service(tmp_path, FakeWriter(draft_article=seven), store).run(
        _job(9)
    )
    assert outcome is not None
    assert outcome.errors[0]["code"] == ERR_SECTION_COUNT_MISMATCH
    assert store.contents == []


async def test_a_timed_out_run_is_failed_and_recoverable(tmp_path: Path) -> None:
    # Scenario: A timed-out run is failed and recoverable
    class SlowWriter(FakeWriter):
        async def draft(self, brief: WriterBrief) -> DraftArticle:
            await asyncio.sleep(1)
            return article()

    store = FakeStore()
    outcome = await _service(tmp_path, SlowWriter(), store, timeout=0.05).run(_job())
    assert outcome is not None
    assert outcome.errors[0]["code"] == ERR_GENERATION_TIMEOUT
    assert outcome.recoverable is True
    assert store.heartbeats >= 1


async def test_cancellation_marks_the_row_and_re_raises(tmp_path: Path) -> None:
    started = asyncio.Event()

    class BlockingWriter(FakeWriter):
        async def draft(self, brief: WriterBrief) -> DraftArticle:
            started.set()
            await asyncio.sleep(10)
            return article()

    store = FakeStore()
    task = asyncio.create_task(_service(tmp_path, BlockingWriter(), store).run(_job()))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert store.outcomes[0].errors[0]["code"] == ERR_GENERATION_CANCELLED
    assert store.outcomes[0].recoverable is True


async def test_a_lost_lease_stops_silently(tmp_path: Path) -> None:
    # Scenario: A stale duplicate task cannot clobber a newer lease
    store = FakeStore(lost=True)
    assert await _service(tmp_path, FakeWriter(), store).run(_job()) is None
    assert store.contents == []
    assert store.outcomes == []


async def test_an_article_the_owner_already_wrote_is_never_overwritten(
    tmp_path: Path,
) -> None:
    store = FakeStore()
    store.content = parse_blog_content({
        "schema": "blog.v2",
        "sections": [{"id": "sec_owner", "heading": None, "body_md": "Meu texto."}],
    }).to_content()
    outcome = await _service(tmp_path, FakeWriter(), store).run(_job())
    assert outcome is not None
    assert outcome.errors[0]["code"] == ERR_GENERATION_CONFLICT
    assert parse_blog_content(store.content).sections[0].body_md == "Meu texto."


async def test_a_failed_image_write_discards_the_new_files(tmp_path: Path) -> None:
    # Review: a failed write leaves no orphan files (AE-0424 discard).
    class FailingAttach(FakeStore):
        async def apply_document(
            self, lease: GenerationLease, change: DocumentApply
        ) -> None:
            if change.images_generated:
                self.fail_writes = True
            await super().apply_document(lease, change)

    store = FailingAttach()
    outcome = await _service(tmp_path, FakeWriter(), store).run(_job(2))
    assert outcome is not None
    assert outcome.errors[0]["code"] == ERR_GENERATION_FAILED
    assert list((tmp_path / POST_ID).iterdir()) == []


async def test_an_unexpected_error_is_a_generic_failure(tmp_path: Path) -> None:
    writer = FakeWriter(draft_error=KeyError("boom"))
    outcome = await _service(tmp_path, writer, FakeStore()).run(_job())
    assert outcome is not None
    assert outcome.errors[0] == {"code": ERR_GENERATION_FAILED, "reason": "KeyError"}


async def test_a_standalone_run_takes_the_writer_title(tmp_path: Path) -> None:
    store = FakeStore()
    await _service(tmp_path, FakeWriter(), store).run(_job(retitle=True))
    assert store.outcomes[0].title == "Título do artigo"


async def test_every_call_runs_in_a_named_blog_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Scenario: Every call is traced with the required metadata
    scopes: list[BlogPhaseScope] = []

    @contextmanager
    def record(scope: BlogPhaseScope, **_kwargs: object) -> Iterator[MagicMock]:
        scopes.append(scope)
        yield MagicMock()

    monkeypatch.setattr(service_module, "blog_phase_trace", record)
    monkeypatch.setattr(image_module, "blog_phase_trace", record)
    await _service(tmp_path, FakeWriter(), FakeStore()).run(_job(2))
    phases = [scope.phase for scope in scopes]
    assert phases.count(PHASE_BLOG_GENERATION) == 1
    assert phases.count(PHASE_BLOG_SECTION_IMAGE) == 3
    assert {scope.project_id for scope in scopes} == {"carousel-1"}
    assert {scope.user_id for scope in scopes} == {"user-1"}
    assert all(scope.agent_name for scope in scopes)


def test_blog_phase_trace_carries_the_required_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict[str, str]] = []

    @contextmanager
    def capture(metadata: dict[str, str], **_kwargs: object) -> Iterator[MagicMock]:
        captured.append(metadata)
        yield MagicMock()

    monkeypatch.setattr(blog_workflow_observability, "propagate_attributes", capture)
    scope = BlogPhaseScope("p", "u", PHASE_BLOG_GENERATION, "blog_writer")
    with blog_workflow_observability.blog_phase_trace(scope):
        pass
    assert captured == [
        {
            "project_id": "p",
            "user_id": "u",
            "phase": PHASE_BLOG_GENERATION,
            "agent_name": "blog_writer",
            "content_type": "blog_post",
        }
    ]


async def test_a_heartbeat_db_blip_never_replaces_the_run_result(
    tmp_path: Path,
) -> None:
    # Review fix 1: a failing heartbeat is logged and the run still finishes.
    class SlowWriter(FakeWriter):
        async def draft(self, brief: WriterBrief) -> DraftArticle:
            await asyncio.sleep(0.3)
            return article()

    store = FakeStore(heartbeat_errors=2)
    outcome = await _service(tmp_path, SlowWriter(), store).run(_job(4))
    assert outcome is not None
    assert outcome.status == GENERATION_STATUS_COMPLETE
    assert store.outcomes == [outcome]
    assert store.heartbeats >= 1  # kept beating after the blips


def _owner_edits(content: dict[str, object]) -> dict[str, object]:
    """The owner, during the image step: deletes section 2, rewrites section 3
    and sets their own image on section 4."""
    document = parse_blog_content(content)
    sections = list(document.sections)
    owned = BlogImage(
        url="https://cdn.example/owner.jpg", alt="Minha foto", source="upload"
    )
    kept = [
        sections[0],
        sections[2].model_copy(update={"body_md": "Texto do dono."}),
        sections[3].model_copy(update={"image": owned}),
    ]
    return document.model_copy(update={"sections": kept}).to_content()


async def test_owner_edits_during_the_image_step_survive(tmp_path: Path) -> None:
    # Review fix 2: images attach by section id onto the CURRENT content.
    store = FakeStore(owner_edit=_owner_edits)
    outcome = await _service(tmp_path, FakeWriter(), store).run(_job(4))
    assert outcome is not None
    assert outcome.status == GENERATION_STATUS_COMPLETE
    document = parse_blog_content(store.content)
    assert len(document.sections) == 3  # the deleted section stays deleted
    assert document.sections[1].body_md == "Texto do dono."
    assert document.sections[1].image is not None
    assert document.sections[2].image is not None
    assert document.sections[2].image.url == "https://cdn.example/owner.jpg"
    # Review C: the images whose slot vanished (deleted section, owner image)
    # are deleted from the store; only the placed ones remain on disk.
    placed = [document.cover, *(s.image for s in document.sections)]
    generated = [
        i.url.rsplit("/", 1)[1] for i in placed if i and i.source == "generated"
    ]
    on_disk = sorted(path.name for path in (tmp_path / POST_ID).iterdir())
    assert len(generated) == 3  # cover + the 2 surviving empty sections
    assert on_disk == sorted(generated)  # the other 2 files were deleted
    assert document.cover is not None


def _images_only_job() -> GenerationJob:
    return GenerationJob(
        lease=GenerationLease(post_id=POST_ID, lease_id="lease-b", lock_version=3),
        trace=GenerationTrace(project_id=POST_ID, user_id="user-1", post_id=POST_ID),
        titles=ImageTitles("Título", "Title"),
    )


async def _partial_store(tmp_path: Path) -> FakeStore:
    """A store holding a finished article whose section 3 image failed."""
    pt = list(sections(4))
    pt[2] = DraftSection(heading=FAIL_IMAGE_MARKER, body_md=pt[2].body_md)
    draft = DraftArticle("T", tuple(pt), "T", english_sections(4))
    store = FakeStore()
    await _service(tmp_path, FakeWriter(draft_article=draft), store).run(_job(4))
    missing = parse_blog_content(store.content).sections[2]
    fixed = missing.model_copy(update={"heading": "Seção 3"})
    document = parse_blog_content(store.content)
    store.content = document.model_copy(
        update={"sections": [*document.sections[:2], fixed, *document.sections[3:]]}
    ).to_content()
    return store


async def test_an_images_only_retry_fills_only_the_empty_slots(tmp_path: Path) -> None:
    # Review fix 3: a retry never regenerates an existing article.
    store = await _partial_store(tmp_path)
    before = parse_blog_content(store.content)
    writer = FakeWriter()
    outcome = await _service(tmp_path, writer, store).run(_images_only_job())
    assert writer.drafts == []  # no writer call
    assert outcome is not None
    assert outcome.status == GENERATION_STATUS_COMPLETE
    assert outcome.image_count == 1
    assert store.generated == 5 + 1  # first run's 5 reserved (one failed) + 1
    after = parse_blog_content(store.content)
    assert [s.body_md for s in after.sections] == [s.body_md for s in before.sections]
    assert after.sections[0].image == before.sections[0].image
    assert after.sections[2].image is not None


async def test_images_generated_earlier_count_against_the_cap(
    tmp_path: Path,
) -> None:
    # Review fix 3: AE-0424's per-post cap counts every attempt + the editor.
    store = await _partial_store(tmp_path)
    assert store.generated == 5  # all 5 slots were reserved before the spend
    store.cap = 5
    outcome = await _service(tmp_path, FakeWriter(), store).run(_images_only_job())
    assert outcome is not None
    assert outcome.image_count == 0
    assert outcome.status == GENERATION_STATUS_PARTIAL
    assert outcome.errors[0]["code"] == "image_cost_cap_reached"
