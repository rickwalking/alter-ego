"""Writer brief from a carousel, the tracked runner, the document.

Feature: backend/tests/features/blog_generate_ae0425.feature
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from rag_backend.application.services.blog import blog_generation_runner as runner
from rag_backend.application.services.blog.blog_brief import (
    CarouselMaterial,
    StandaloneMaterial,
    carousel_brief,
    standalone_brief,
)
from rag_backend.application.services.blog.blog_generated_document import (
    GeneratedLanguages,
    ImageTitles,
    attach_images,
    build_generated_document,
    missing_image_subjects,
)
from rag_backend.application.services.blog.blog_generation_service import (
    GenerationJob,
)
from rag_backend.domain.models.blog_document import BlogImage
from rag_backend.domain.models.blog_generation import (
    GatedLanguage,
    GenerationLease,
    GenerationOutcome,
    GenerationTrace,
    QualityFindings,
    VoiceScore,
)
from rag_backend.domain.models.carousel import CarouselSlide
from rag_backend.domain.models.persona import PersonaProfile
from tests.blog_generation_fakes import brief, sections

STATE = {
    "research_findings": [
        {"summary": "Agents write code.", "key_points": ["fast", "cheap"]},
        {"summary": "Agents write code.", "key_points": ["fast", "cheap"]},
        {"summary": " ", "key_points": []},
        "garbage",
    ],
    "outline": [
        {"title": "Abertura", "key_points": ["gancho"]},
        {"title": "", "key_points": []},
    ],
}


def _slide(number: int, note: object) -> CarouselSlide:
    return CarouselSlide(
        project_id=uuid4(),
        slide_number=number,
        slide_type="content",
        heading=f"Slide {number}",
        body="corpo",
        extras={"long_form_notes": note},
    )


def test_carousel_brief_uses_the_artifact_as_raw_material() -> None:
    # Scenario: From-carousel always creates a draft (inputs = research + outline + notes)
    material = CarouselMaterial(
        title="Título",
        topic="Agentes",
        persona=PersonaProfile(),
        section_count=9,
        slides=(_slide(2, "Nota dois."), _slide(1, "Nota um."), _slide(3, None)),
        state=STATE,
    )
    result = carousel_brief(material)
    assert result.section_count == 9
    assert result.research == ("Agents write code. fast cheap",)
    assert [point.title for point in result.outline] == ["Abertura"]
    assert result.outline[0].key_points == ("gancho",)
    assert result.notes == ("Nota um.", "Nota dois.")


def test_carousel_brief_without_a_checkpoint() -> None:
    material = CarouselMaterial("T", "t", PersonaProfile(), 7, state=None)
    result = carousel_brief(material)
    assert result.research == ()
    assert result.outline == ()


def test_standalone_brief_uses_the_default_count() -> None:
    # Scenario: Standalone generation uses the content-mode default
    result = standalone_brief(
        StandaloneMaterial("Um tópico", PersonaProfile(), 7, ("https://a.example",))
    )
    assert result.section_count == 7
    assert result.title == result.topic == "Um tópico"
    assert result.source_urls == ("https://a.example",)


def _gated(count: int, prefix: str) -> GatedLanguage:
    return GatedLanguage(
        sections=sections(count, prefix),
        voice=VoiceScore(80.0, {"overall": 80.0, "suggestions": ["x"]}),
        findings=QualityFindings(banned_phrases=("em resumo",)),
        rewrite_passes=1,
    )


def test_document_shares_ids_and_attaches_images_by_slot() -> None:
    """The lede has no heading."""
    languages = GeneratedLanguages(
        _gated(3, "Seção"), _gated(3, "Section"), "Título", "Title"
    )
    document = build_generated_document(languages, "2026-10-18T12:00:00Z")
    assert document.quality is not None
    assert document.quality.rewrite_passes == 1
    assert document.quality.repetition.banned_phrases == ["em resumo"]
    subjects = missing_image_subjects(document, "Título")
    assert [subject.slot for subject in subjects] == [
        "cover",
        *(s.id for s in document.sections),
    ]
    assert subjects[1].heading == "Título"
    image = BlogImage(url="/api/blog-images/p/a.jpg", alt="Título")
    attached = attach_images(
        document,
        {"cover": image, document.sections[2].id: image},
        ImageTitles(languages.title, languages.en_title),
    )
    assert attached.cover is not None
    assert attached.sections[1].image is None
    assert attached.sections[2].image is not None
    assert attached.sections[2].image.alt == "Seção 3"
    english = attached.translations["en"]
    assert english.cover is not None
    assert english.cover.alt == "Title"
    assert english.sections[2].image is not None
    assert english.sections[2].image.alt == "Section 3"


class _RecordingService:
    def __init__(
        self, gate: asyncio.Event | None = None, error: Exception | None = None
    ) -> None:
        self.ran: list[GenerationJob] = []
        self._gate = gate
        self._error = error

    async def run(self, job: GenerationJob) -> GenerationOutcome | None:
        self.ran.append(job)
        if self._error is not None:
            raise self._error
        if self._gate is not None:
            await self._gate.wait()
        return None


def _job() -> GenerationJob:
    return GenerationJob(
        lease=GenerationLease("post-1", "lease", 1),
        brief=brief(1),
        trace=GenerationTrace("p", "u", "post-1"),
    )


async def test_schedule_tracks_the_task_until_it_finishes() -> None:
    # Scenario: The 202 run is a tracked in-process task with a lease and heartbeat
    service = _RecordingService()
    task = runner.schedule_blog_generation(service, _job())
    assert task.get_name() == "blog-generation-post-1"
    assert task in runner.running_blog_generation_tasks()
    await task
    await asyncio.sleep(0)
    assert task not in runner.running_blog_generation_tasks()
    assert len(service.ran) == 1


async def test_a_crashing_run_is_logged_not_raised() -> None:
    task = runner.schedule_blog_generation(
        _RecordingService(error=KeyError("x")), _job()
    )
    await task
    assert task.exception() is None


async def test_shutdown_cancels_in_flight_runs() -> None:
    service = _RecordingService(gate=asyncio.Event())
    task = runner.schedule_blog_generation(service, _job())
    await asyncio.sleep(0)
    assert await runner.cancel_blog_generation_tasks() == 1
    assert task.cancelled()


def test_attach_keeps_owner_images_and_skips_filled_slots() -> None:
    """Only empty slots are filled, so a retry asks only for the gaps."""
    languages = GeneratedLanguages(
        _gated(2, "Seção"), _gated(2, "Section"), "Título", "Title"
    )
    document = build_generated_document(languages, "2026-10-18T12:00:00Z")
    owner = BlogImage(url="https://cdn.example/mine.jpg", alt="Minha")
    first = document.sections[0].model_copy(update={"image": owner})
    document = document.model_copy(update={"sections": [first, document.sections[1]]})
    assert [s.slot for s in missing_image_subjects(document, "T")] == [
        "cover",
        document.sections[1].id,
    ]
    generated = BlogImage(url="/api/blog-images/p/b.jpg", alt="x")
    attached = attach_images(
        document,
        {document.sections[0].id: generated, "gone": generated},
        ImageTitles("Título", "Title"),
    )
    assert attached.sections[0].image == owner
    assert attached.cover is None
