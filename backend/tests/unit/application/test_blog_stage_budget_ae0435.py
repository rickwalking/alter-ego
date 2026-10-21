"""Stage budgets of the blog generation run + the EN gate in the run (AE-0435).

Feature: backend/tests/features/blog_generation_en_gate_timeout_ae0435.feature
"""

from __future__ import annotations

import asyncio
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from rag_backend.application.services.blog import (
    blog_generation_service,
    blog_image_batch,
    blog_image_service,
)
from rag_backend.application.services.blog.blog_generation_service import (
    BlogGenerationDeps,
    BlogGenerationService,
    GenerationJob,
    GenerationTimings,
)
from rag_backend.application.services.blog.blog_image_batch import (
    BlogImageBatchService,
    ImageBatchRequest,
)
from rag_backend.application.services.blog.blog_quality_gate import (
    BlogQualityGate,
    QualityGateDeps,
)
from rag_backend.domain.constants.blog_generation import (
    BLOG_EN_MAX_RETRANSLATIONS,
    ERR_EN_WRONG_LANGUAGE,
    ERR_GENERATION_TIMEOUT,
    ERR_IMAGE_TIMEOUT,
    GENERATION_STATUS_COMPLETE,
    GENERATION_STATUS_FAILED,
    GENERATION_STATUS_PARTIAL,
    IMAGE_SLOT_COVER,
)
from rag_backend.domain.models.blog_document import parse_blog_content
from rag_backend.domain.models.blog_generation import (
    DraftArticle,
    GenerationLease,
    GenerationTrace,
    ImageSubject,
    WriterBrief,
)
from tests.blog_generation_fakes import (
    FakeImageGenerator,
    FakeScorer,
    FakeStore,
    FakeTranslator,
    FakeWriter,
    article,
    brief,
    english_gate,
    image_batch,
    sections,
)

POST_ID = "44444444-4444-4444-8444-444444444444"
SLOW_MARKER = "SLOW_IMAGE"
TRACE = GenerationTrace(project_id="carousel-1", user_id="user-1", post_id=POST_ID)


@pytest.fixture(autouse=True)
def _no_langfuse(monkeypatch: pytest.MonkeyPatch) -> None:
    for module in (blog_generation_service, blog_image_batch):
        monkeypatch.setattr(
            module,
            "blog_phase_trace",
            lambda _scope, **_kwargs: nullcontext(MagicMock()),
        )
    monkeypatch.setattr(
        blog_image_service,
        "blog_ai_propagate",
        lambda *_a: nullcontext(MagicMock()),
    )


@dataclass
class SlowImageGenerator(FakeImageGenerator):
    """Never finishes a prompt with ``SLOW_MARKER`` (an image call that hangs)."""

    started: list[str] = field(default_factory=list)

    async def generate_image(self, prompt: str, output_path: str) -> str:
        self.started.append(prompt)
        if SLOW_MARKER in prompt:
            await asyncio.sleep(30)
        return await super().generate_image(prompt, output_path)


def _timings(text: float = 5.0, wave: float = 5.0) -> GenerationTimings:
    return GenerationTimings(
        text_timeout_seconds=text, image_wave_seconds=wave, heartbeat_seconds=0.01
    )


@dataclass(frozen=True)
class _Run:
    writer: FakeWriter = field(default_factory=FakeWriter)
    translator: FakeTranslator = field(default_factory=FakeTranslator)
    generator: FakeImageGenerator = field(default_factory=FakeImageGenerator)
    timings: GenerationTimings = field(default_factory=_timings)


def _service(tmp: Path, run: _Run, store: FakeStore) -> BlogGenerationService:
    gate = BlogQualityGate(QualityGateDeps(writer=run.writer, scorer=FakeScorer()))
    return BlogGenerationService(
        BlogGenerationDeps(
            writer=run.writer,
            gate=gate,
            english=english_gate(gate, run.translator),
            images=image_batch(tmp, run.generator),
            store=store,
            timings=run.timings,
        )
    )


def _job(count: int = 4) -> GenerationJob:
    return GenerationJob(
        lease=GenerationLease(post_id=POST_ID, lease_id="lease-a", lock_version=1),
        brief=brief(count),
        trace=TRACE,
    )


def _subjects(*headings: str) -> tuple[ImageSubject, ...]:
    return tuple(
        ImageSubject(slot=f"slot-{index}", heading=heading, body="Corpo.")
        for index, heading in enumerate(headings)
    )


class TestImagesBudget:
    # Scenario: The images stage has its own budget, sized by the slot count
    @pytest.mark.parametrize(
        ("slots", "concurrency", "expected"), [(5, 2, 3.0), (4, 2, 2.0), (1, 3, 1.0)]
    )
    def test_budget_is_one_wave_per_concurrency_batch(
        self, tmp_path: Path, slots: int, concurrency: int, expected: float
    ) -> None:
        batch = image_batch(tmp_path, FakeImageGenerator(), concurrency)
        request = ImageBatchRequest(TRACE, (), max_images=slots, wave_seconds=1.0)
        assert batch.budget_seconds(request, slots) == expected

    def test_no_wave_budget_means_unbounded(self, tmp_path: Path) -> None:
        batch = image_batch(tmp_path, FakeImageGenerator())
        request = ImageBatchRequest(TRACE, (), max_images=3)
        assert batch.budget_seconds(request, 3) is None

    # Scenario: An images stage that runs out of time keeps the finished images
    async def test_a_timeout_keeps_finished_images_and_names_the_rest(
        self, tmp_path: Path
    ) -> None:
        batch: BlogImageBatchService = image_batch(tmp_path, SlowImageGenerator())
        subjects = _subjects("Um", "Dois", SLOW_MARKER, SLOW_MARKER)
        result = await batch.generate(
            ImageBatchRequest(TRACE, subjects, max_images=4, wave_seconds=0.1)
        )
        assert set(result.images) == {"slot-0", "slot-1"}
        assert [error["slot"] for error in result.errors] == ["slot-2", "slot-3"]
        assert {error["code"] for error in result.errors} == {ERR_IMAGE_TIMEOUT}


class TestStageBudgetsInTheRun:
    # Scenario: A text stage that runs out of time fails the run as before
    async def test_a_text_timeout_fails_and_stores_nothing(
        self, tmp_path: Path
    ) -> None:
        class SlowWriter(FakeWriter):
            async def draft(self, brief: WriterBrief) -> DraftArticle:
                await asyncio.sleep(1)
                return article()

        store = FakeStore()
        run = _Run(writer=SlowWriter(), timings=_timings(text=0.05))
        outcome = await _service(tmp_path, run, store).run(_job())
        assert outcome is not None
        assert outcome.status == GENERATION_STATUS_FAILED
        assert outcome.errors[0]["code"] == ERR_GENERATION_TIMEOUT
        assert outcome.recoverable is True
        assert store.contents == []

    # Scenario: The images stage has its own budget (text time not taken from it)
    async def test_text_time_is_not_taken_from_the_images_budget(
        self, tmp_path: Path
    ) -> None:
        class SlowWriter(FakeWriter):
            async def draft(self, brief: WriterBrief) -> DraftArticle:
                await asyncio.sleep(0.3)
                return article()

        store = FakeStore()
        run = _Run(writer=SlowWriter(), timings=_timings(text=5, wave=0.25))
        outcome = await _service(tmp_path, run, store).run(_job())
        assert outcome is not None
        assert outcome.status == GENERATION_STATUS_COMPLETE
        assert outcome.image_count == 5

    # Scenario: An images stage that runs out of time keeps the finished images
    async def test_an_images_timeout_attaches_finished_images_and_is_partial(
        self, tmp_path: Path
    ) -> None:
        # Cover + sections 1-2 finish; sections 3-4 hang (their heading is slow).
        drafts = list(sections(4))
        drafts[2] = drafts[2].__class__(heading=SLOW_MARKER, body_md=drafts[2].body_md)
        drafts[3] = drafts[3].__class__(heading=SLOW_MARKER, body_md=drafts[3].body_md)
        draft = DraftArticle("T", tuple(drafts), "T", article().en_sections)
        store = FakeStore()
        run = _Run(
            writer=FakeWriter(draft_article=draft),
            generator=SlowImageGenerator(),
            timings=_timings(wave=0.1),
        )
        outcome = await _service(tmp_path, run, store).run(_job())
        assert outcome is not None
        assert outcome.status == GENERATION_STATUS_PARTIAL
        assert outcome.recoverable is True
        assert outcome.image_count == 3
        codes = [(error["code"], error.get("slot")) for error in outcome.errors]
        assert len(codes) == 2
        assert {code for code, _slot in codes} == {ERR_IMAGE_TIMEOUT}
        stored = parse_blog_content(store.contents[-1])
        assert stored.cover is not None
        assert [section.image is not None for section in stored.sections] == [
            True,
            True,
            False,
            False,
        ]
        assert {slot for _code, slot in codes} == {
            stored.sections[2].id,
            stored.sections[3].id,
        }
        assert IMAGE_SLOT_COVER not in {slot for _code, slot in codes}


class TestEnglishGateInTheRun:
    # Scenario: Portuguese EN sections are retranslated from the gated PT article
    async def test_a_portuguese_en_is_retranslated_with_the_pt_ids(
        self, tmp_path: Path
    ) -> None:
        draft = DraftArticle("T", sections(4), "T", sections(4, "Seção"))
        store = FakeStore()
        run = _Run(writer=FakeWriter(draft_article=draft))
        outcome = await _service(tmp_path, run, store).run(_job())
        assert outcome is not None
        assert outcome.status == GENERATION_STATUS_COMPLETE
        stored = parse_blog_content(store.contents[-1])
        english = stored.translations["en"]
        assert [s.id for s in english.sections] == [s.id for s in stored.sections]
        assert english.sections[1].body_md.startswith("Paragraph number")
        assert len(run.translator.calls) == 1

    # Scenario: The retranslation is bounded and never stores Portuguese as English
    async def test_a_portuguese_en_that_stays_portuguese_is_never_stored(
        self, tmp_path: Path
    ) -> None:
        draft = DraftArticle("T", sections(4), "T", sections(4, "Seção"))
        store = FakeStore()
        run = _Run(
            writer=FakeWriter(draft_article=draft),
            translator=FakeTranslator(outcomes=["pt"]),
        )
        outcome = await _service(tmp_path, run, store).run(_job())
        assert outcome is not None
        assert outcome.status == GENERATION_STATUS_PARTIAL
        assert outcome.recoverable is True
        assert outcome.errors[0]["code"] == ERR_EN_WRONG_LANGUAGE
        assert outcome.image_count == 5  # images still generated
        assert len(run.translator.calls) == BLOG_EN_MAX_RETRANSLATIONS
        stored = parse_blog_content(store.contents[-1])
        assert stored.translations == {}
        assert all(section.image is not None for section in stored.sections)
