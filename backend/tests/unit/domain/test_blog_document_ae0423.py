"""Unit tests for the blog.v2 document model and the fence-aware splitter (AE-0423).

Feature: backend/tests/features/blog_sections_ae0423.feature
"""

from __future__ import annotations

import itertools

import pytest

from rag_backend.domain.constants.blog_document import (
    BLOG_SCHEMA_V2,
    ERR_BLOG_DOCUMENT_NOT_OBJECT,
    ERR_BLOG_DOCUMENT_NOT_V2,
    ERR_INVALID_BLOG_DOCUMENT,
)
from rag_backend.domain.models.blog_document import (
    InvalidBlogDocumentError,
    parse_blog_content,
)
from rag_backend.domain.models.blog_document_split import (
    build_language_document,
    convert_legacy_content,
    extract_legacy_markdown,
    is_v2_content,
    join_language_document,
    migrate_content,
    new_section_id,
    rollback_content,
    split_markdown,
)

SEC_A = "sec_aaaaaaaa-0000-4000-8000-000000000001"
SEC_B = "sec_bbbbbbbb-0000-4000-8000-000000000002"
SEC_C = "sec_cccccccc-0000-4000-8000-000000000003"


def _image(alt: str = "Diagrama do fluxo", url: str = "https://cdn/x.jpg") -> dict:
    return {"url": url, "alt": alt, "source": "generated", "prompt": "p", "model": "m"}


def _section(section_id: str, heading: str | None = "H", body: str = "Body") -> dict:
    return {"id": section_id, "heading": heading, "body_md": body, "image": None}


def _doc(**overrides: object) -> dict:
    base: dict = {
        "schema": BLOG_SCHEMA_V2,
        "cover": None,
        "sections": [_section(SEC_A)],
        "translations": {},
        "quality": None,
    }
    base.update(overrides)
    return base


def _counter_factory():
    counter = itertools.count(1)
    return lambda: f"sec_{next(counter)}"


class TestParseBlogContent:
    # Scenario: A valid blog.v2 document parses to cover + ordered sections
    def test_valid_document_parses_cover_and_ordered_sections(self) -> None:
        sections = [
            {**_section(SEC_A, "Um"), "image": _image()},
            _section(SEC_B, "Dois"),
            _section(SEC_C, None),
        ]
        document = parse_blog_content(_doc(cover=_image("Capa"), sections=sections))

        assert document.cover is not None
        assert document.cover.alt == "Capa"
        assert [s.id for s in document.sections] == [SEC_A, SEC_B, SEC_C]
        assert [s.heading for s in document.sections] == ["Um", "Dois", None]
        assert document.sections[0].image is not None
        assert document.sections[0].image.alt == "Diagrama do fluxo"
        assert document.to_content()["schema"] == BLOG_SCHEMA_V2

    # Scenario: A non-v2 write shape is rejected, never coerced
    def test_flat_markdown_string_is_rejected_not_coerced(self) -> None:
        with pytest.raises(InvalidBlogDocumentError) as exc:
            parse_blog_content("# Title\n\n## A\n\nBody")
        assert exc.value.code == ERR_BLOG_DOCUMENT_NOT_OBJECT

    def test_legacy_markdown_object_is_rejected(self) -> None:
        with pytest.raises(InvalidBlogDocumentError) as exc:
            parse_blog_content({"markdown": "## A\n\nBody"})
        assert exc.value.code == ERR_BLOG_DOCUMENT_NOT_V2

    # Scenario: Malformed JSONB is rejected
    @pytest.mark.parametrize("content", [[], [{"schema": "blog.v2"}], None, 7])
    def test_non_object_content_is_rejected(self, content: object) -> None:
        with pytest.raises(InvalidBlogDocumentError) as exc:
            parse_blog_content(content)
        assert exc.value.code == ERR_BLOG_DOCUMENT_NOT_OBJECT

    def test_other_schema_value_is_rejected(self) -> None:
        with pytest.raises(InvalidBlogDocumentError) as exc:
            parse_blog_content(_doc(schema="blog.v1"))
        assert exc.value.code == ERR_BLOG_DOCUMENT_NOT_V2

    # Scenario: A section image with an empty alt is rejected on write
    @pytest.mark.parametrize("alt", ["", "   "])
    def test_empty_alt_is_rejected(self, alt: str) -> None:
        sections = [{**_section(SEC_A), "image": _image(alt=alt)}]
        with pytest.raises(InvalidBlogDocumentError) as exc:
            parse_blog_content(_doc(sections=sections))
        assert exc.value.code == ERR_INVALID_BLOG_DOCUMENT
        assert "alt" in exc.value.message

    # Scenario: Duplicate section ids are rejected
    def test_duplicate_section_ids_are_rejected(self) -> None:
        with pytest.raises(InvalidBlogDocumentError):
            parse_blog_content(_doc(sections=[_section(SEC_A), _section(SEC_A)]))

    def test_duplicate_ids_in_a_translation_are_rejected(self) -> None:
        translation = {
            "schema": BLOG_SCHEMA_V2,
            "sections": [_section(SEC_A), _section(SEC_A)],
        }
        with pytest.raises(InvalidBlogDocumentError):
            parse_blog_content(_doc(translations={"en": translation}))

    @pytest.mark.parametrize(
        "url",
        ["http://x/y.jpg", "javascript:alert(1)", "//evil/x.jpg", "x.jpg"],
    )
    def test_image_url_must_be_https_or_same_origin(self, url: str) -> None:
        with pytest.raises(InvalidBlogDocumentError):
            parse_blog_content(_doc(cover=_image(url=url)))

    def test_same_origin_path_is_accepted(self) -> None:
        document = parse_blog_content(_doc(cover=_image(url="/blog-images/a.jpg")))
        assert document.cover is not None
        assert document.cover.url == "/blog-images/a.jpg"

    def test_unknown_keys_are_rejected(self) -> None:
        with pytest.raises(InvalidBlogDocumentError):
            parse_blog_content(_doc(markdown="legacy"))

    def test_invalid_section_id_is_rejected(self) -> None:
        with pytest.raises(InvalidBlogDocumentError):
            parse_blog_content(_doc(sections=[_section("not-a-section-id")]))

    def test_invalid_translation_language_is_rejected(self) -> None:
        translation = {"schema": BLOG_SCHEMA_V2, "sections": [_section(SEC_A)]}
        with pytest.raises(InvalidBlogDocumentError):
            parse_blog_content(_doc(translations={"EN-us": translation}))

    # Scenario: An in-progress draft may have zero sections and a null quality
    def test_empty_sections_and_null_quality_parse(self) -> None:
        document = parse_blog_content(_doc(sections=[], quality=None))
        assert document.sections == []
        assert document.quality is None

    def test_quality_and_translation_quality_parse(self) -> None:
        quality = {"voice_score": 82.0, "rewrite_passes": 1}
        translation = {
            "schema": BLOG_SCHEMA_V2,
            "sections": [_section(SEC_B)],
            "quality": quality,
        }
        document = parse_blog_content(
            _doc(quality=quality, translations={"en": translation})
        )
        assert document.quality is not None
        assert document.quality.voice_score == 82.0
        assert document.translations["en"].quality is not None


class TestSplitMarkdown:
    # Scenario: A v1 row is cut over in place and the old shape is dropped
    def test_leading_h1_is_stripped_and_empty_lede_dropped(self) -> None:
        md = (
            "# GPT 5.6 saiu\n\n## O que aconteceu\n\nA OpenAI.\n\n"
            "## Por que importa\n\nPara quem.\n"
        )
        chunks = split_markdown(md)
        assert [(c.heading, c.body) for c in chunks] == [
            ("O que aconteceu", "A OpenAI."),
            ("Por que importa", "Para quem."),
        ]

    def test_lede_text_after_the_h1_is_kept(self) -> None:
        chunks = split_markdown("# T\n\nIntro.\n\n## A\n\nBody")
        assert [(c.heading, c.body) for c in chunks] == [
            (None, "Intro."),
            ("A", "Body"),
        ]

    def test_h1_that_is_not_the_first_line_is_kept(self) -> None:
        chunks = split_markdown("Intro.\n# Not a title\n")
        assert chunks[0].body == "Intro.\n# Not a title"

    # Scenario: A "## " line inside a fenced code block is not a section boundary
    @pytest.mark.parametrize("fence", ["```", "~~~", "````"])
    def test_h2_inside_a_fence_is_not_a_boundary(self, fence: str) -> None:
        md = f"## A\n\nText\n\n{fence}python\n## comment\n{fence}\n\n## B\n\nEnd"
        chunks = split_markdown(md)
        assert [c.heading for c in chunks] == ["A", "B"]
        assert f"{fence}python\n## comment\n{fence}" in chunks[0].body

    def test_shorter_closing_fence_does_not_close(self) -> None:
        md = "## A\n\n````\n```\n## still code\n````\n\n## B\n\nx"
        assert [c.heading for c in split_markdown(md)] == ["A", "B"]

    def test_other_fence_char_does_not_close(self) -> None:
        md = "## A\n\n```\n~~~\n## still code\n```\n\n## B\n\nx"
        assert [c.heading for c in split_markdown(md)] == ["A", "B"]

    def test_h3_is_not_a_boundary(self) -> None:
        chunks = split_markdown("## A\n\n### Sub\n\nx")
        assert len(chunks) == 1
        assert chunks[0].body == "### Sub\n\nx"

    def test_headed_chunk_without_body_is_kept(self) -> None:
        chunks = split_markdown("## Only heading\n")
        assert [(c.heading, c.body) for c in chunks] == [("Only heading", "")]

    # Scenario: The cutover stores the raw body without sanitizing
    def test_body_bytes_are_raw(self) -> None:
        body = "A &amp; B <b>x</b> [l](https://a.b/(c)) `code` **bold**\n\n- item"
        chunks = split_markdown(f"## H\n\n{body}\n")
        assert chunks[0].body == body

    def test_empty_markdown_has_no_chunks(self) -> None:
        assert split_markdown("") == []


class TestBuildAndConvert:
    # Scenario: An H1-only stub migrates to a single section
    def test_h1_only_stub_becomes_one_empty_section(self) -> None:
        document = build_language_document("# A title with no body", new_section_id)
        sections = document["sections"]
        assert isinstance(sections, list)
        assert len(sections) == 1
        assert sections[0]["body_md"] == ""
        assert sections[0]["heading"] is None
        parse_blog_content(document)

    def test_section_ids_are_unique_sec_uuid4(self) -> None:
        document = build_language_document("## A\n\nx\n\n## B\n\ny")
        sections = document["sections"]
        assert isinstance(sections, list)
        ids = [str(section["id"]) for section in sections]
        assert len(set(ids)) == 2
        assert all(i.startswith("sec_") and len(i) == 40 for i in ids)

    # Scenario: Every string translation is cut over with the same rules
    def test_translations_are_converted_with_the_same_rules(self) -> None:
        content = {
            "markdown": "## PT\n\nCorpo",
            "translations": {"en": "# Title\n\n## What happened\n\nBody"},
        }
        converted = convert_legacy_content(content, _counter_factory())
        translations = converted["translations"]
        assert isinstance(translations, dict)
        en = translations["en"]
        assert en["schema"] == BLOG_SCHEMA_V2
        assert [(s["heading"], s["body_md"]) for s in en["sections"]] == [
            ("What happened", "Body")
        ]
        assert en["cover"] is None
        assert en["quality"] is None
        parse_blog_content(converted)

    # Scenario: A non-string translation entry is dropped, not stringified
    def test_non_string_translation_is_dropped(self) -> None:
        content = {"markdown": "x", "translations": {"en": {"a": 1}, "es": 3}}
        converted = convert_legacy_content(content)
        assert converted["translations"] == {}
        sections = converted["sections"]
        assert isinstance(sections, list)
        bodies = [section["body_md"] for section in sections]
        assert bodies == ["x"]
        assert all("{'" not in str(body) for body in bodies)

    # Scenario: A non-markdown content object does not become str(dict) garbage
    @pytest.mark.parametrize(
        "content", [{"foo": {"bar": 1}}, None, [], {"markdown": 5}, 3]
    )
    def test_non_markdown_content_becomes_one_empty_section(
        self, content: object
    ) -> None:
        converted = convert_legacy_content(content)
        sections = converted["sections"]
        assert isinstance(sections, list)
        assert len(sections) == 1
        assert sections[0]["body_md"] == ""
        assert converted["cover"] is None
        assert converted["quality"] is None
        parse_blog_content(converted)

    def test_body_key_and_raw_string_are_legacy_markdown(self) -> None:
        assert extract_legacy_markdown({"body": "b"}) == "b"
        assert extract_legacy_markdown({"markdown": "m", "body": "b"}) == "m"
        assert extract_legacy_markdown("raw") == "raw"

    def test_translations_not_a_dict_are_ignored(self) -> None:
        converted = convert_legacy_content({"markdown": "x", "translations": "en"})
        assert converted["translations"] == {}


class TestMigrateAndDetect:
    # Scenario: The cutover is idempotent
    def test_v2_content_is_a_noop(self) -> None:
        assert migrate_content(_doc()) is None

    def test_v1_content_is_converted(self) -> None:
        migrated = migrate_content({"markdown": "## A\n\nx"})
        assert migrated is not None
        assert is_v2_content(migrated)

    def test_v2_top_level_with_string_translation_is_fixed(self) -> None:
        pt = [_section(SEC_A, "Mantido")]
        content = _doc(
            sections=pt,
            translations={
                "en": "## E\n\nen",
                "es": {"schema": BLOG_SCHEMA_V2, "sections": []},
                "de": 4,
            },
        )
        migrated = migrate_content(content)
        assert migrated is not None
        assert migrated["sections"] == pt
        translations = migrated["translations"]
        assert isinstance(translations, dict)
        assert set(translations) == {"en", "es"}
        assert is_v2_content(migrated)

    def test_v2_top_level_with_non_dict_translations(self) -> None:
        migrated = migrate_content(_doc(translations="en"))
        assert migrated is not None
        assert migrated["translations"] == {}

    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            (None, False),
            ({"markdown": "x"}, False),
            ({"schema": BLOG_SCHEMA_V2}, True),
            ({"schema": BLOG_SCHEMA_V2, "translations": {"en": "x"}}, False),
            ({"schema": BLOG_SCHEMA_V2, "translations": []}, False),
        ],
    )
    def test_is_v2_content(self, content: object, expected: bool) -> None:
        assert is_v2_content(content) is expected


class TestRollback:
    # Scenario: --rollback re-joins sections to text-equivalent markdown
    def test_round_trip_preserves_section_body_bytes(self) -> None:
        md = (
            "# T\n\n## Um\n\nA &amp; <i>b</i>\n\n```\n## c\n```\n\n"
            "## Dois\n\n  indented\ttab\n"
        )
        en = "## One\n\nBody EN"
        converted = convert_legacy_content({"markdown": md, "translations": {"en": en}})
        restored = rollback_content(converted)

        assert restored["markdown"] == (
            "## Um\n\nA &amp; <i>b</i>\n\n```\n## c\n```\n\n## Dois\n\n  indented\ttab"
        )
        assert restored["translations"] == {"en": en}
        again = split_markdown(str(restored["markdown"]))
        first = split_markdown(md)
        assert [c.body for c in again] == [c.body for c in first]
        assert "# T" not in str(restored["markdown"])

    def test_lede_section_rejoins_without_heading(self) -> None:
        document = build_language_document("Intro.\n\n## A\n\nx")
        assert join_language_document(document) == "Intro.\n\n## A\n\nx"

    @pytest.mark.parametrize(
        "document", [None, {"sections": "x"}, {"sections": [1, {"body_md": 2}]}]
    )
    def test_join_tolerates_malformed_documents(self, document: object) -> None:
        assert join_language_document(document) in {"", "\n\n"}

    def test_rollback_of_non_dict_has_empty_translations(self) -> None:
        assert rollback_content(None) == {"markdown": "", "translations": {}}
