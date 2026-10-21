"""One-shot repair of stored posts whose EN reads as Portuguese.

Feature: backend/tests/features/blog_generation_en_gate_timeout_ae0435.feature
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field

import pytest

from rag_backend.application.services.blog.blog_en_repair import (
    BlogEnRepairService,
    EnRepairDeps,
    EnRepairReport,
    StoredPost,
    WrongEnglish,
    wrong_english_sections,
)
from rag_backend.application.services.blog.blog_translation_service import (
    BlogTranslationError,
)
from rag_backend.domain.models.blog_document import (
    BlogLanguageDocument,
    parse_blog_content,
)
from rag_backend.domain.models.blog_generation import DraftSection
from rag_backend.scripts import regenerate_blog_en
from tests.blog_generation_fakes import FakeTranslator, english_sections, sections

IMAGE = {"url": "https://cdn.example/blog-images/p/a.jpg", "alt": "Arte"}
PT_IDS = ("sec_one", "sec_two")


def _language(
    drafts: tuple[DraftSection, ...], ids: tuple[str, ...]
) -> dict[str, object]:
    return {
        "schema": "blog.v2",
        "cover": IMAGE,
        "sections": [
            {
                "id": section_id,
                "heading": draft.heading,
                "body_md": draft.body_md,
                "image": IMAGE,
            }
            for section_id, draft in zip(ids, drafts, strict=True)
        ],
        "quality": None,
    }


def _content(english: str | None) -> dict[str, object]:
    content = _language(sections(2), PT_IDS)
    variants = {
        "pt": _language(sections(2, "Seção"), PT_IDS),
        "en": _language(english_sections(2), PT_IDS),
    }
    content["translations"] = {} if english is None else {"en": variants[english]}
    return content


@dataclass
class FakeRepairStore:
    """In-memory posts + the EN writes the repair made."""

    rows: dict[str, StoredPost] = field(default_factory=dict)
    writes: list[tuple[str, BlogLanguageDocument]] = field(default_factory=list)

    def add(self, post_id: str, content: object) -> None:
        self.rows[post_id] = StoredPost(post_id, f"Post {post_id}", content)

    async def posts(self) -> list[StoredPost]:
        return list(self.rows.values())

    async def post(self, post_id: str) -> StoredPost | None:
        return self.rows.get(post_id)

    async def replace_english(
        self, post_id: str, english: BlogLanguageDocument
    ) -> None:
        self.writes.append((post_id, english))


def _service(
    store: FakeRepairStore, translator: FakeTranslator | None = None
) -> BlogEnRepairService:
    return BlogEnRepairService(
        EnRepairDeps(store=store, translator=translator or FakeTranslator())
    )


def _store() -> FakeRepairStore:
    store = FakeRepairStore()
    store.add("pt-en", _content("pt"))
    store.add("en-ok", _content("en"))
    store.add("no-en", _content(None))
    store.add("legacy", {"body": "old"})
    return store


class TestScan:
    # Scenario: The scan lists posts whose EN reads as Portuguese (read-only)
    async def test_lists_only_the_portuguese_en_and_writes_nothing(self) -> None:
        store = _store()
        report = await _service(store).scan()
        assert [item.post_id for item in report.wrong] == ["pt-en"]
        assert report.wrong[0].sections == ("#1", "Seção 2")
        assert store.writes == []

    def test_no_en_is_not_wrong(self) -> None:
        assert wrong_english_sections(parse_blog_content(_content(None))) is None


class TestRepair:
    # Scenario: --apply regenerates only the EN of the named post
    async def test_replaces_en_keeping_pt_ids_images_and_cover(self) -> None:
        store = _store()
        report = await _service(store).repair(("pt-en",))
        assert report.repaired == ["pt-en"]
        ((post_id, english),) = store.writes
        assert post_id == "pt-en"
        assert [section.id for section in english.sections] == list(PT_IDS)
        assert all(section.image is not None for section in english.sections)
        assert english.cover is not None
        assert english.quality is None
        assert english.sections[0].body_md.startswith("Paragraph number")

    # Scenario: --apply leaves an English EN untouched
    @pytest.mark.parametrize(
        ("post_id", "reason"),
        [
            ("en-ok", "en_reads_as_english"),
            ("no-en", "no_en_translation"),
            ("legacy", "not_blog_v2"),
            ("missing", "not_found"),
        ],
    )
    async def test_skips_what_needs_no_repair(self, post_id: str, reason: str) -> None:
        store = _store()
        report = await _service(store).repair((post_id,))
        assert report.skipped == [(post_id, reason)]
        assert store.writes == []

    async def test_a_failed_translation_is_reported_and_writes_nothing(self) -> None:
        store = _store()
        translator = FakeTranslator(outcomes=[BlogTranslationError("boom")])
        report = await _service(store, translator).repair(("pt-en",))
        assert report.failed == [("pt-en", "boom")]
        assert store.writes == []


class TestScript:
    def test_apply_without_only_is_a_usage_error(self) -> None:
        assert regenerate_blog_en.main(["--apply"]) == regenerate_blog_en.EXIT_USAGE

    def test_the_default_mode_is_the_scan(self) -> None:
        args = regenerate_blog_en.build_parser().parse_args([])
        assert args.apply is False
        assert args.only == []

    async def test_run_mode_dispatches_scan_and_repair(self) -> None:
        store = _store()
        parser = regenerate_blog_en.build_parser()
        scan = await regenerate_blog_en.run_mode(_service(store), parser.parse_args([]))
        assert [item.post_id for item in scan.wrong] == ["pt-en"]
        apply: argparse.Namespace = parser.parse_args(["--apply", "--only", "pt-en"])
        repair = await regenerate_blog_en.run_mode(_service(store), apply)
        assert repair.repaired == ["pt-en"]

    def test_report_lines(self) -> None:
        report = EnRepairReport(
            wrong=[WrongEnglish("a", "Título", ("#1",))],
            repaired=["b"],
            skipped=[("c", "not_found")],
            failed=[("d", "boom")],
        )
        assert regenerate_blog_en.format_report(report) == [
            "summary: wrong_en=1 repaired=1 skipped=1 failed=1",
            "  wrong-en a sections=#1 Título",
            "  repaired b",
            "  skipped  c (not_found)",
            "  failed   d (boom)",
        ]
