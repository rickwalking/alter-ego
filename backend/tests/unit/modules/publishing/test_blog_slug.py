"""Unit tests for server-side blog slug generation (AE-0411).

Feature: blog_dashboard_ae0411.feature (create scenarios)
"""

import re

from rag_backend.modules.publishing.domain.blog_slug import (
    build_blog_slug,
    new_slug_suffix,
    slugify_title,
    with_generated_slug,
)

_SUFFIX_RE = re.compile(r"^[0-9a-f]{8}$")


class TestSlugifyTitle:
    def test_lowercases_and_hyphenates(self) -> None:
        assert slugify_title("Untitled Draft") == "untitled-draft"

    def test_drops_accents_and_punctuation(self) -> None:
        assert slugify_title("  Revisão humana: é QA!  ") == "revisao-humana-e-qa"

    def test_title_without_ascii_falls_back(self) -> None:
        assert slugify_title("🚀🚀") == "post"
        assert slugify_title("") == "post"

    def test_long_title_is_capped_without_trailing_hyphen(self) -> None:
        stem = slugify_title("a" * 79 + " b" * 40)
        assert len(stem) <= 80
        assert not stem.endswith("-")


class TestBuildSlug:
    def test_joins_stem_and_suffix(self) -> None:
        assert build_blog_slug("My Post", "1a2b3c4d") == "my-post-1a2b3c4d"

    def test_suffix_is_short_hex_and_varies(self) -> None:
        first, second = new_slug_suffix(), new_slug_suffix()
        assert _SUFFIX_RE.match(first)
        assert first != second


class TestWithGeneratedSlug:
    # Scenario: Creating two posts without a slug succeeds
    def test_missing_slug_is_generated_from_title(self) -> None:
        payload: dict[str, object] = {"title": "Untitled draft"}
        result = with_generated_slug(payload)
        slug = str(result["slug"])
        assert slug.startswith("untitled-draft-")
        assert _SUFFIX_RE.match(slug.removeprefix("untitled-draft-"))
        assert "slug" not in payload  # input not mutated

    # Scenario: A blank slug is generated like a missing one
    def test_blank_or_none_slug_is_generated(self) -> None:
        assert str(
            with_generated_slug({"title": "X", "slug": "  "})["slug"]
        ).startswith("x-")
        assert str(
            with_generated_slug({"title": "X", "slug": None})["slug"]
        ).startswith("x-")

    # Scenario: A given slug is kept
    def test_given_slug_is_kept_stripped(self) -> None:
        assert with_generated_slug({"title": "X", "slug": " mine "})["slug"] == "mine"

    def test_non_string_title_uses_fallback_stem(self) -> None:
        assert str(with_generated_slug({"title": None})["slug"]).startswith("post-")
