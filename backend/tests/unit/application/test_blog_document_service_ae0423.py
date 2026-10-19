"""Unit tests for BlogDocumentService + the public projection (AE-0423).

Feature: backend/tests/features/blog_sections_ae0423.feature
"""

from __future__ import annotations

import pytest
from structlog.testing import capture_logs

from rag_backend.application.services.blog.blog_document_service import (
    BlogDocumentService,
    is_generation_in_progress,
)
from rag_backend.application.services.blog.blog_public_projection import (
    project_public_document,
)
from rag_backend.domain.constants.blog_document import (
    BLOG_HEADING_MAX_CHARS,
    BLOG_SCHEMA_V2,
    BLOG_SECTION_MAX_CHARS,
    ERR_BLOG_HEADING_INVALID,
    ERR_BLOG_NO_SECTIONS,
    ERR_BLOG_NOT_PUBLISHABLE,
    ERR_BLOG_SECTION_TOO_LONG,
    METRIC_BLOG_V2_NON_MIGRATED_ROWS,
)
from rag_backend.domain.models.blog_document import (
    BlogImage,
    InvalidBlogDocumentError,
    parse_blog_content,
)

SEC_A = "sec_aaaaaaaa-0000-4000-8000-000000000001"
SEC_B = "sec_bbbbbbbb-0000-4000-8000-000000000002"
IN_PROGRESS = {"generation": {"status": "in_progress"}}


def _image(url: str = "https://cdn/x.jpg", alt: str = "Alt") -> dict:
    return {
        "url": url,
        "alt": alt,
        "caption": "Legenda",
        "source": "generated",
        "prompt": "secret prompt",
        "model": "gpt-image-2",
        "created_at": "2026-10-18T12:00:00Z",
    }


def _section(section_id: str = SEC_A, **overrides: object) -> dict:
    base: dict = {"id": section_id, "heading": "H", "body_md": "Body", "image": None}
    base.update(overrides)
    return base


def _doc(**overrides: object) -> dict:
    base: dict = {
        "schema": BLOG_SCHEMA_V2,
        "cover": None,
        "sections": [_section()],
        "translations": {},
        "quality": None,
    }
    base.update(overrides)
    return base


QUALITY = {
    "voice_score": 80.0,
    "voice_breakdown": {"tone_match": 81.0, "suggestions": ["x"]},
    "repetition": {"repeated_sentences": ["r"], "banned_phrases": []},
    "rewrite_passes": 1,
    "checked_at": "2026-10-18T12:00:00Z",
}


class TestValidateForWrite:
    # Scenario: featured_image_url tracks cover.url on save
    def test_featured_image_url_is_the_cover_url(self) -> None:
        write = BlogDocumentService.validate_for_write(_doc(cover=_image()))
        assert write.featured_image_url == "https://cdn/x.jpg"
        cover = write.content["cover"]
        assert isinstance(cover, dict)
        assert cover["url"] == "https://cdn/x.jpg"

    # Scenario: Removing the cover clears featured_image_url
    def test_null_cover_projects_null(self) -> None:
        write = BlogDocumentService.validate_for_write(_doc(cover=None))
        assert write.featured_image_url is None
        assert write.content["cover"] is None

    # Scenario: Writes remain strict while the read fail-safe is active
    def test_legacy_shape_is_rejected(self) -> None:
        with pytest.raises(InvalidBlogDocumentError):
            BlogDocumentService.validate_for_write({"markdown": "## A\n\nx"})

    # Scenario: A section image with an empty alt is rejected on write
    def test_empty_alt_is_rejected(self) -> None:
        sections = [_section(image=_image(alt=""))]
        with pytest.raises(InvalidBlogDocumentError):
            BlogDocumentService.validate_for_write(_doc(sections=sections))

    # Scenario: Duplicate section ids are rejected
    def test_duplicate_ids_are_rejected(self) -> None:
        with pytest.raises(InvalidBlogDocumentError):
            BlogDocumentService.validate_for_write(
                _doc(sections=[_section(), _section()])
            )

    # Scenario: An in-progress draft may have zero sections and a null quality
    def test_zero_sections_only_while_generation_in_progress(self) -> None:
        with pytest.raises(InvalidBlogDocumentError) as exc:
            BlogDocumentService.validate_for_write(_doc(sections=[]))
        assert exc.value.code == ERR_BLOG_NO_SECTIONS
        write = BlogDocumentService.validate_for_write(
            _doc(sections=[]), generation_in_progress=True
        )
        assert write.content["sections"] == []

    def test_translation_needs_sections_too(self) -> None:
        translation = {"schema": BLOG_SCHEMA_V2, "sections": []}
        with pytest.raises(InvalidBlogDocumentError) as exc:
            BlogDocumentService.validate_for_write(
                _doc(translations={"en": translation})
            )
        assert exc.value.code == ERR_BLOG_NO_SECTIONS

    def test_oversized_section_is_rejected_on_write(self) -> None:
        body = "x" * (BLOG_SECTION_MAX_CHARS + 1)
        with pytest.raises(InvalidBlogDocumentError) as exc:
            BlogDocumentService.validate_for_write(
                _doc(sections=[_section(body_md=body)])
            )
        assert exc.value.code == ERR_BLOG_SECTION_TOO_LONG

    def test_section_at_the_limit_is_accepted(self) -> None:
        body = "x" * BLOG_SECTION_MAX_CHARS
        BlogDocumentService.validate_for_write(_doc(sections=[_section(body_md=body)]))

    @pytest.mark.parametrize(
        "heading", ["# Title", "  ## H", "", "   ", "x" * (BLOG_HEADING_MAX_CHARS + 1)]
    )
    def test_invalid_heading_is_rejected(self, heading: str) -> None:
        with pytest.raises(InvalidBlogDocumentError) as exc:
            BlogDocumentService.validate_for_write(
                _doc(sections=[_section(heading=heading)])
            )
        assert exc.value.code == ERR_BLOG_HEADING_INVALID

    @pytest.mark.parametrize("heading", [None, "C# tips", "x" * BLOG_HEADING_MAX_CHARS])
    def test_valid_heading_is_accepted(self, heading: str | None) -> None:
        BlogDocumentService.validate_for_write(
            _doc(sections=[_section(heading=heading)])
        )


class TestInitialContentAndCover:
    def test_initial_content_is_a_valid_one_section_document(self) -> None:
        content = BlogDocumentService.initial_content()
        document = parse_blog_content(content)
        assert len(document.sections) == 1
        assert document.sections[0].body_md == ""
        assert document.cover is None
        assert content["translations"] == {}

    def test_with_cover_sets_and_projects(self) -> None:
        cover = BlogImage(url="https://cdn/c.jpg", alt="Capa")
        write = BlogDocumentService.with_cover(_doc(), cover)
        assert write.featured_image_url == "https://cdn/c.jpg"
        stored = write.content["cover"]
        assert isinstance(stored, dict)
        assert stored["alt"] == "Capa"

    def test_with_cover_none_clears_projection(self) -> None:
        write = BlogDocumentService.with_cover(_doc(cover=_image()), None)
        assert write.featured_image_url is None
        assert write.content["cover"] is None

    def test_with_cover_rejects_a_legacy_row(self) -> None:
        with pytest.raises(InvalidBlogDocumentError):
            BlogDocumentService.with_cover({"markdown": "x"}, None)


class TestPublishGuard:
    # Scenario: A null cover does not block publish and cards use a fallback
    def test_null_cover_with_body_is_publishable(self) -> None:
        BlogDocumentService.assert_publishable(_doc(cover=None))

    # Scenario: An in-progress draft ... publish validation rejects it
    @pytest.mark.parametrize(
        "sections", [[], [_section(body_md="")], [_section(body_md="  \n")]]
    )
    def test_no_non_empty_section_is_not_publishable(self, sections: list) -> None:
        with pytest.raises(InvalidBlogDocumentError) as exc:
            BlogDocumentService.assert_publishable(_doc(sections=sections))
        assert exc.value.code == ERR_BLOG_NOT_PUBLISHABLE

    def test_legacy_row_is_not_publishable(self) -> None:
        with pytest.raises(InvalidBlogDocumentError) as exc:
            BlogDocumentService.assert_publishable({"markdown": "## A\n\nx"})
        assert exc.value.code == ERR_BLOG_NOT_PUBLISHABLE


class TestReadFailSafe:
    # Scenario: A non-migrated legacy row is read through the temporary fail-safe
    def test_legacy_row_reads_as_text_only_v2_and_emits_metric(self) -> None:
        legacy = {
            "markdown": "# T\n\n## A\n\nCorpo",
            "translations": {"en": "## E\n\nBody"},
        }
        with capture_logs() as logs:
            document = BlogDocumentService.read_document(legacy, "post-1")

        assert document.cover is None
        assert document.quality is None
        assert [(s.heading, s.body_md, s.image) for s in document.sections] == [
            ("A", "Corpo", None)
        ]
        assert document.translations["en"].sections[0].body_md == "Body"
        events = [
            entry
            for entry in logs
            if entry["event"] == METRIC_BLOG_V2_NON_MIGRATED_ROWS
        ]
        assert events
        assert events[0]["post_id"] == "post-1"

    def test_valid_v2_row_reads_without_metric(self) -> None:
        with capture_logs() as logs:
            document = BlogDocumentService.read_document(_doc(), "post-2")
        assert document.sections[0].id == SEC_A
        assert not logs

    def test_broken_v2_row_reads_as_an_empty_document(self) -> None:
        broken = _doc(sections=[_section(), _section()])
        document = BlogDocumentService.read_document(broken, "post-3")
        assert len(document.sections) == 1
        assert document.sections[0].body_md == ""

    @pytest.mark.parametrize("content", [None, [], "flat markdown", {"x": 1}])
    def test_any_non_v2_content_never_raises(self, content: object) -> None:
        document = BlogDocumentService.read_document(content, "post-4")
        assert len(document.sections) == 1


class TestGenerationFlag:
    @pytest.mark.parametrize(
        ("metadata", "expected"),
        [
            (IN_PROGRESS, True),
            ({"generation": {"status": "complete"}}, False),
            ({"generation": "in_progress"}, False),
            ({}, False),
            (None, False),
        ],
    )
    def test_is_generation_in_progress(self, metadata: object, expected: bool) -> None:
        assert is_generation_in_progress(metadata) is expected


class TestPublicProjection:
    # Scenario: The public payload is a projection without internal fields
    def test_projection_excludes_quality_prompt_and_model(self) -> None:
        translation = {
            "schema": BLOG_SCHEMA_V2,
            "cover": _image("https://cdn/en.jpg"),
            "sections": [_section(SEC_B, image=_image("https://cdn/s.jpg"))],
            "quality": QUALITY,
        }
        document = parse_blog_content(
            _doc(
                cover=_image(),
                sections=[_section(image=_image("/blog-images/1.jpg", "Diagrama"))],
                quality=QUALITY,
                translations={"en": translation},
            )
        )
        projected = project_public_document(document)

        text = repr(projected)
        assert "quality" not in projected
        assert "prompt" not in text
        assert "model" not in text
        translations = projected["translations"]
        assert isinstance(translations, dict)
        assert "quality" not in translations["en"]
        # Scenario: A published v2 post serializes its own section images
        sections = projected["sections"]
        assert isinstance(sections, list)
        assert sections[0]["image"] == {
            "url": "/blog-images/1.jpg",
            "alt": "Diagrama",
            "caption": "Legenda",
            "source": "generated",
            "created_at": "2026-10-18T12:00:00Z",
        }
        cover = projected["cover"]
        assert isinstance(cover, dict)
        assert cover["url"] == "https://cdn/x.jpg"
        assert projected["schema"] == BLOG_SCHEMA_V2
        en_sections = translations["en"]["sections"]
        assert en_sections[0]["image"]["url"] == "https://cdn/s.jpg"

    def test_projection_keeps_null_images(self) -> None:
        projected = project_public_document(parse_blog_content(_doc()))
        assert projected["cover"] is None
        sections = projected["sections"]
        assert isinstance(sections, list)
        assert sections[0]["image"] is None
        assert projected["translations"] == {}
