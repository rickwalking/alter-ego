"""The blog generation run end to end with fakes (AE-0425).

Feature: backend/tests/features/blog_generate_ae0425.feature
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

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
from rag_backend.domain.models.blog_document import parse_blog_content
from rag_backend.domain.models.blog_generation import (
    ContentWrite,
    DraftArticle,
    DraftSection,
    GenerationConflictError,
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
        monkeypatch.setattr(module, "blog_phase_trace", lambda _scope: nullcontext())
    # The editor's single-image service (AE-0424) traces with its own helper.
    from rag_backend.application.services.blog import blog_image_service as _single

    monkeypatch.setattr(_single, "blog_ai_propagate", lambda *_a: nullcontext())


def _service(
    tmp: Path,
    writer: FakeWriter,
    store: FakeStore,
    timeout: float = 5.0,
    cap: float = 5.0,
) -> BlogGenerationService:
    images = image_batch(tmp, FakeImageGenerator())
    gate = BlogQualityGate(
        QualityGateDeps(writer=writer, scorer=FakeScorer(scores=[82.0]))
    )
    return BlogGenerationService(
        BlogGenerationDeps(
            writer=writer,
            gate=gate,
            images=images,
            store=store,
            timings=GenerationTimings(timeout_seconds=timeout, heartbeat_seconds=0.01),
            image_cost_cap_usd=cap,
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


def _final(store: FakeStore) -> ContentWrite:
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
    document = parse_blog_content(_final(store).content)
    assert len(document.sections) == 4
    assert document.cover is not None
    assert all(section.image is not None for section in document.sections)
    assert _final(store).featured_image_url == document.cover.url
    # Scenario: The voice score is mirrored for the listing badge
    assert document.quality is not None
    assert document.quality.voice_score == 82.0
    assert store.contents[0].voice_score == 82.0  # the article write
    # EN translation: same ids, own quality, own alt text.
    english = document.translations["en"]
    assert [s.id for s in english.sections] == [s.id for s in document.sections]
    assert english.quality is not None
    assert english.sections[1].image is not None
    assert english.sections[1].image.alt == "Section 2"
    assert store.contents[0].title is None
    assert store.outcomes == [outcome]


async def test_section_and_slot_count_follow_the_slide_count(tmp_path: Path) -> None:
    # Scenario: Section and image count follow the carousel slide count
    writer = FakeWriter(draft_article=article(9))
    store = FakeStore()
    outcome = await _service(tmp_path, writer, store).run(_job(9))
    document = parse_blog_content(_final(store).content)
    assert len(document.sections) == 9
    assert outcome is not None
    assert outcome.image_count == 10


async def test_a_failed_image_makes_the_run_partial(tmp_path: Path) -> None:
    # Scenario: A failed image leaves the slot empty and does not fail the draft
    pt = list(sections(4))
    pt[2] = DraftSection(heading=FAIL_IMAGE_MARKER, body_md=pt[2].body_md)
    draft = DraftArticle("T", tuple(pt), "T", sections(4, "Section"))
    store = FakeStore()
    outcome = await _service(tmp_path, FakeWriter(draft_article=draft), store).run(
        _job(4)
    )
    assert outcome is not None
    assert outcome.status == GENERATION_STATUS_PARTIAL
    document = parse_blog_content(_final(store).content)
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
    seven = DraftArticle("T", sections(7), "T", sections(7, "Section"))
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


async def test_an_owner_edit_during_the_run_is_a_conflict(tmp_path: Path) -> None:
    class ConflictStore(FakeStore):
        async def write_content(
            self, lease: GenerationLease, write: ContentWrite
        ) -> None:
            raise GenerationConflictError(lease.post_id)

    store = ConflictStore()
    outcome = await _service(tmp_path, FakeWriter(), store).run(_job())
    assert outcome is not None
    assert outcome.errors[0]["code"] == ERR_GENERATION_CONFLICT


async def test_an_unexpected_error_is_a_generic_failure(tmp_path: Path) -> None:
    writer = FakeWriter(draft_error=KeyError("boom"))
    outcome = await _service(tmp_path, writer, FakeStore()).run(_job())
    assert outcome is not None
    assert outcome.errors[0] == {"code": ERR_GENERATION_FAILED, "reason": "KeyError"}


async def test_a_standalone_run_takes_the_writer_title(tmp_path: Path) -> None:
    store = FakeStore()
    await _service(tmp_path, FakeWriter(), store).run(_job(retitle=True))
    assert store.contents[0].title == "Título do artigo"


async def test_every_call_runs_in_a_named_blog_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Scenario: Every call is traced with the required metadata
    scopes: list[BlogPhaseScope] = []

    @contextmanager
    def record(scope: BlogPhaseScope) -> Iterator[None]:
        scopes.append(scope)
        yield

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
    def capture(metadata: dict[str, str]) -> Iterator[None]:
        captured.append(metadata)
        yield

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
    owned = {
        "url": "https://cdn.example/owner.jpg",
        "alt": "Minha foto",
        "source": "upload",
    }
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
    assert document.cover is not None
    assert _final(store).featured_image_url == document.cover.url


def _images_only_job(prior: float = 0.0) -> GenerationJob:
    return GenerationJob(
        lease=GenerationLease(post_id=POST_ID, lease_id="lease-b", lock_version=3),
        trace=GenerationTrace(project_id=POST_ID, user_id="user-1", post_id=POST_ID),
        titles=ImageTitles("Título", "Title"),
        prior_image_spend_usd=prior,
    )


async def _partial_store(tmp_path: Path) -> FakeStore:
    """A store holding a finished article whose section 3 image failed."""
    pt = list(sections(4))
    pt[2] = DraftSection(heading=FAIL_IMAGE_MARKER, body_md=pt[2].body_md)
    draft = DraftArticle("T", tuple(pt), "T", sections(4, "Section"))
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
    assert outcome.image_spend_usd == pytest.approx(0.25)
    after = parse_blog_content(store.content)
    assert [s.body_md for s in after.sections] == [s.body_md for s in before.sections]
    assert after.sections[0].image == before.sections[0].image
    assert after.sections[2].image is not None


async def test_spend_from_earlier_attempts_counts_against_the_cap(
    tmp_path: Path,
) -> None:
    # Review fix 3: the cap is per post, across attempts.
    store = await _partial_store(tmp_path)
    outcome = await _service(tmp_path, FakeWriter(), store, cap=1.25).run(
        _images_only_job(prior=1.25)
    )
    assert outcome is not None
    assert outcome.image_count == 0
    assert outcome.image_spend_usd == 0.0
    assert outcome.status == GENERATION_STATUS_PARTIAL
    assert outcome.errors[0]["code"] == "image_cost_cap_reached"


async def test_a_full_run_records_its_image_spend(tmp_path: Path) -> None:
    store = FakeStore()
    outcome = await _service(tmp_path, FakeWriter(), store).run(_job(4))
    assert outcome is not None
    assert outcome.image_spend_usd == pytest.approx(1.25)
