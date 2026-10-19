"""Fakes for the AE-0425 blog writer / quality gate / image tests.

Feature: backend/tests/features/blog_generate_ae0425.feature
The fakes implement the domain ports (``BlogArticleWriter``, ``VoiceScorer``,
``ImagePromptBuilder``, ``ImageGenerationService``, ``BlogGenerationStore``)
and record every call so the tests assert behavior (how many rewrites, which
slots got images, what was written under which lease).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from rag_backend.application.services.asset_cdn_service import AssetCdnService
from rag_backend.application.services.blog.blog_image_batch import (
    BlogImageBatchDeps,
    BlogImageBatchService,
)
from rag_backend.application.services.blog.blog_image_service import BlogImageService
from rag_backend.application.services.blog.blog_image_store import BlogImageStore
from rag_backend.domain.models.blog_generation import (
    DocumentApply,
    DraftArticle,
    DraftSection,
    GenerationLease,
    GenerationOutcome,
    JudgeRequest,
    RewriteRequest,
    VoiceScore,
    WriterBrief,
    WriterFailedError,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.domain.protocols import ImageGenerationService

FAIL_IMAGE_MARKER = "FAIL_IMAGE"


def sections(count: int, prefix: str = "Seção") -> tuple[DraftSection, ...]:
    """``count`` distinct sections; the first is the lede (no heading)."""
    return tuple(
        DraftSection(
            heading=None if index == 0 else f"{prefix} {index + 1}",
            body_md=(
                f"Parágrafo único número {index + 1} com uma ideia própria sobre o "
                f"assunto, contada na primeira pessoa e sem repetir nada ({prefix})."
            ),
        )
        for index in range(count)
    )


def article(count: int = 4) -> DraftArticle:
    """A clean PT + EN article of ``count`` sections."""
    return DraftArticle(
        title="Título do artigo",
        sections=sections(count),
        en_title="Article title",
        en_sections=sections(count, "Section"),
    )


def brief(count: int = 4, **overrides: object) -> WriterBrief:
    """A writer brief with ``count`` roles (``overrides`` replace fields)."""
    from rag_backend.application.services.blog.blog_section_plan import (
        narrative_roles,
    )

    base = WriterBrief(
        title="Título do artigo",
        topic="Agentes de IA no trabalho",
        section_roles=narrative_roles(count),
        persona=PersonaProfile(name="Pedro"),
    )
    return dataclasses.replace(base, **overrides)


@dataclass
class FakeWriter:
    """Returns a fixed draft; rewrites with ``rewrite_to`` (or the same sections)."""

    draft_article: DraftArticle = field(default_factory=article)
    rewrite_to: Callable[[RewriteRequest], tuple[DraftSection, ...]] | None = None
    notes: tuple[str, ...] = ("Seção 2: corte a frase repetida.",)
    draft_error: Exception | None = None
    drafts: list[WriterBrief] = field(default_factory=list)
    rewrites: list[RewriteRequest] = field(default_factory=list)
    judgements: list[JudgeRequest] = field(default_factory=list)

    async def draft(self, brief: WriterBrief) -> DraftArticle:
        self.drafts.append(brief)
        if self.draft_error is not None:
            raise self.draft_error
        return self.draft_article

    async def rewrite(self, request: RewriteRequest) -> tuple[DraftSection, ...]:
        self.rewrites.append(request)
        if self.rewrite_to is not None:
            return self.rewrite_to(request)
        return request.sections

    async def judge(self, request: JudgeRequest) -> tuple[str, ...]:
        self.judgements.append(request)
        return self.notes


@dataclass
class FakeScorer:
    """Returns the queued scores in order (the last one repeats)."""

    scores: list[float] = field(default_factory=lambda: [82.0])
    texts: list[str] = field(default_factory=list)
    error: Exception | None = None

    async def score(self, text: str) -> VoiceScore:
        self.texts.append(text)
        if self.error is not None:
            raise self.error
        value = self.scores.pop(0) if len(self.scores) > 1 else self.scores[0]
        return VoiceScore(
            overall=value, breakdown={"overall": value, "tone_match": value}
        )


def image_prompt(scene: str) -> str:
    """Stand-in for the versioned template: keeps the scene so the fake
    generator can fail a chosen slot by its heading."""
    return f"Editorial photo. No text, no words, no letters. Scene: {scene}"


def image_batch(
    root: Path, generator: ImageGenerationService, concurrency: int = 2
) -> BlogImageBatchService:
    """The batch service over the editor's (AE-0424) single-image service."""
    store = BlogImageStore(root=root, cdn=AssetCdnService())
    service = BlogImageService(generator, store, image_prompt)
    return BlogImageBatchService(
        BlogImageBatchDeps(images=service, store=store, concurrency=concurrency)
    )


@dataclass
class FakeImageGenerator:
    """Writes JPEG bytes to ``output_path``; fails when the prompt has the marker."""

    prompts: list[str] = field(default_factory=list)
    write_file: bool = True
    # False = the provider recovered: the marker no longer fails (retry tests).
    honor_marker: bool = True

    async def generate_image(self, prompt: str, output_path: str) -> str:
        self.prompts.append(prompt)
        if self.honor_marker and FAIL_IMAGE_MARKER in prompt:
            raise RuntimeError("provider refused the prompt")
        if self.write_file:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")
        return output_path


@dataclass
class FakeStore:
    """An in-memory row: ``content`` + recorded writes.

    ``lost`` makes every write raise ``LeaseLostError``; ``heartbeat_errors``
    makes that many heartbeats raise ``ConnectionError`` (a DB blip);
    ``owner_edit`` mutates the content right before a write (an owner save
    during the run); ``fail_writes`` makes content writes fail (discard runs).
    """

    content: dict[str, object] = field(default_factory=dict)
    contents: list[dict[str, object]] = field(default_factory=list)
    applied: list[DocumentApply] = field(default_factory=list)
    outcomes: list[GenerationOutcome] = field(default_factory=list)
    heartbeats: int = 0
    heartbeat_errors: int = 0
    generated: int = 0  # reserved images (AE-0424 counter)
    cap: int = 30
    lost: bool = False
    fail_writes: bool = False
    owner_edit: Callable[[dict[str, object]], dict[str, object]] | None = None

    async def heartbeat(self, lease: GenerationLease) -> None:
        self._check(lease)
        if self.heartbeat_errors > 0:
            self.heartbeat_errors -= 1
            raise ConnectionError("db blip")
        self.heartbeats += 1

    async def read_content(self, lease: GenerationLease) -> dict[str, object]:
        self._check(lease)
        return self.content

    async def reserve_images(self, lease: GenerationLease, wanted: int) -> int:
        self._check(lease)
        granted = max(0, min(wanted, self.cap - self.generated))
        self.generated += granted
        return granted

    async def apply_document(
        self, lease: GenerationLease, change: DocumentApply
    ) -> None:
        from rag_backend.domain.models.blog_document import parse_blog_content

        self._check(lease)
        if self.fail_writes:
            if change.discard is not None:
                change.discard()
            raise ConnectionError("write failed")
        if self.owner_edit is not None and self.content:
            self.content = self.owner_edit(self.content)
        latest = parse_blog_content(self.content or _bootstrap())
        self.content = change.edit(latest).to_content()
        self.contents.append(self.content)
        self.applied.append(change)

    async def finish(self, lease: GenerationLease, outcome: GenerationOutcome) -> None:
        self._check(lease)
        self.outcomes.append(outcome)

    def _check(self, lease: GenerationLease) -> None:
        from rag_backend.domain.models.blog_generation import LeaseLostError

        if self.lost:
            raise LeaseLostError(lease.post_id)


def _bootstrap() -> dict[str, object]:
    return {
        "schema": "blog.v2",
        "cover": None,
        "sections": [],
        "translations": {},
        "quality": None,
    }


def writer_failure() -> WriterFailedError:
    """The error the writer raises after error/timeout/empty/bad JSON."""
    return WriterFailedError("blog writer failed: invalid_json")
