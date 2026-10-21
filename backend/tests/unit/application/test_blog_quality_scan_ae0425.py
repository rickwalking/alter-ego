"""Deterministic quality scan + section plan of the blog writer.

Feature: backend/tests/features/blog_generate_ae0425.feature
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.blog.blog_quality_scan import (
    ScanInput,
    normalize_sentence,
    reads_as_english,
    scan_sections,
    split_sentences,
    strip_source_leaks,
)
from rag_backend.application.services.blog.blog_section_plan import (
    SectionCountSource,
    default_section_count,
    narrative_roles,
    normalize_section_count,
    resolve_section_count,
)
from rag_backend.domain.constants.blog_voice import ROLE_CLOSE, ROLE_LEDE
from rag_backend.domain.models.blog_generation import (
    DraftSection,
    SectionCountMismatchError,
)

REPEATED = (
    "A inteligência artificial mudou a forma como eu escrevo código todos os dias."
)
ORACLE = (
    "QUARANTINE_ORACLE_7f3a marks the English research intro that must never reach PT."
)


def _section(body: str, heading: str | None = "Título") -> DraftSection:
    return DraftSection(heading=heading, body_md=body)


class TestRepetition:
    # Scenario: Seeded repetition is detected
    def test_names_the_sentence_restated_in_two_sections(self) -> None:
        found = scan_sections(
            ScanInput(
                language="pt",
                sections=(
                    _section(f"{REPEATED} Depois disso tudo mudou."),
                    _section(f"Outra ideia nova aqui. {REPEATED}"),
                ),
            )
        )
        assert found.repeated_sentences == (REPEATED,)
        assert found.has_findings

    def test_short_connectives_are_not_repetition(self) -> None:
        found = scan_sections(
            ScanInput(
                language="pt",
                sections=(
                    _section("Mas não é só isso."),
                    _section("Mas não é só isso."),
                ),
            )
        )
        assert found.repeated_sentences == ()
        assert not found.has_findings

    # Scenario: The writer produces one continuous article, not per-slide concatenation
    def test_a_note_copied_verbatim_is_reported(self) -> None:
        note = "Eu passei três semanas testando agentes de código no meu fluxo de trabalho real."
        found = scan_sections(
            ScanInput(
                language="pt",
                sections=(_section(f"Comecei assim. {note}"),),
                notes=(note,),
            )
        )
        assert found.repeated_sentences == (note,)

    def test_markdown_and_case_do_not_hide_a_repeat(self) -> None:
        assert normalize_sentence("**A IA**   mudou TUDO.") == "a ia mudou tudo"
        assert split_sentences("Um. Dois!\n\nTrês?") == ["Um.", "Dois!", "Três?"]


class TestBannedPhrases:
    # Scenario: A banned stock phrase is detected
    def test_pt_phrase_is_named(self) -> None:
        found = scan_sections(
            ScanInput(
                language="pt", sections=(_section("No mundo de hoje, tudo é IA."),)
            )
        )
        assert found.banned_phrases == ("no mundo de hoje",)

    def test_en_list_applies_to_the_translation(self) -> None:
        found = scan_sections(
            ScanInput(language="en", sections=(_section("In conclusion, ship it."),))
        )
        assert found.banned_phrases == ("in conclusion",)

    def test_phrase_inside_a_longer_word_is_not_matched(self) -> None:
        found = scan_sections(
            ScanInput(
                language="pt", sections=(_section("Em resumos longos eu me perco."),)
            )
        )
        assert "em resumo" not in found.banned_phrases


class TestSourceLeak:
    # Scenario: No English research text leaks into the PT sections
    def test_research_sentence_is_dropped_from_pt(self) -> None:
        sections = (
            _section(
                f"Primeira frase em português sobre o tema. {ORACLE}\n\nOutro parágrafo."
            ),
        )
        cleaned, dropped = strip_source_leaks(sections, (f"Intro. {ORACLE}",))
        assert dropped == 1
        assert "QUARANTINE_ORACLE_7f3a" not in cleaned[0].body_md
        assert (
            cleaned[0].body_md
            == "Primeira frase em português sobre o tema.\n\nOutro parágrafo."
        )

    def test_nothing_to_strip_returns_the_same_sections(self) -> None:
        sections = (_section("Texto."),)
        assert strip_source_leaks(sections, ()) == (sections, 0)


class TestSectionCount:
    # Scenario: Section and image count follow the carousel slide count
    def test_project_slide_count_wins(self) -> None:
        source = SectionCountSource(
            slide_count=9, slides_config="1 intro, 3 content", content_mode="pov"
        )
        assert resolve_section_count(source) == 9

    def test_slides_config_is_next(self) -> None:
        source = SectionCountSource(
            slides_config="1 intro, 3 content, 1 closing, 1 cta"
        )
        assert resolve_section_count(source) == 6

    def test_zero_slide_count_falls_through(self) -> None:
        assert (
            resolve_section_count(SectionCountSource(slide_count=0, content_mode="pov"))
            == 9
        )

    # Scenario: Standalone generation uses the content-mode default
    def test_content_mode_defaults(self) -> None:
        assert resolve_section_count(SectionCountSource()) == 7
        assert default_section_count("pov_news") == 9
        assert default_section_count(None) == 7

    def test_roles_are_distinct_with_lede_and_close(self) -> None:
        roles = narrative_roles(9)
        assert len(roles) == 9
        assert len(set(roles)) == 9
        assert roles[0] == ROLE_LEDE
        assert roles[-1] == ROLE_CLOSE
        assert narrative_roles(1) == (ROLE_LEDE,)
        assert narrative_roles(2) == (ROLE_LEDE, ROLE_CLOSE)


class TestNormalizeCount:
    # Scenario: A writer section-count mismatch is not silently stored
    def test_exact_count_is_unchanged(self) -> None:
        sections = (_section("A"), _section("B"))
        assert normalize_section_count(sections, 2) == sections

    def test_extra_sections_are_merged_into_the_last(self) -> None:
        sections = (_section("A", "1"), _section("B", "2"), _section("C", "3"))
        merged = normalize_section_count(sections, 2)
        assert [s.body_md for s in merged] == ["A", "B\n\nC"]
        assert merged[1].heading == "2"

    def test_missing_sections_are_split_on_paragraphs(self) -> None:
        sections = (_section("Um.\n\nDois.\n\nTrês.\n\nQuatro.", "H"),)
        split = normalize_section_count(sections, 2)
        assert [s.body_md for s in split] == ["Um.\n\nDois.", "Três.\n\nQuatro."]
        assert split[0].heading == "H"
        assert split[1].heading is None

    def test_seven_one_paragraph_sections_cannot_become_nine(self) -> None:
        sections = tuple(_section(f"Parágrafo {i}.") for i in range(7))
        with pytest.raises(SectionCountMismatchError):
            normalize_section_count(sections, 9)

    def test_no_sections_fails(self) -> None:
        with pytest.raises(SectionCountMismatchError):
            normalize_section_count((), 3)


class TestEnglishInPortuguese:
    """A PT section that reads as English is a finding."""

    ENGLISH = (
        "The agents are changing the way that we work, and it is clear that this "
        "is only the start of the shift for the teams that have them."
    )

    def test_an_english_pt_section_is_reported(self) -> None:
        found = scan_sections(
            ScanInput(
                language="pt",
                sections=(
                    _section("Eu escrevo em português, com calma."),
                    _section(self.ENGLISH, "Dois"),
                ),
            )
        )
        assert found.english_sections == ("Dois",)
        assert found.has_findings

    def test_portuguese_with_english_terms_is_fine(self) -> None:
        text = "Eu uso o agent loop com tool calling e prompt caching no meu fluxo de trabalho, mas não é mágica."
        assert not reads_as_english(text)
        assert reads_as_english(self.ENGLISH)

    def test_the_en_translation_is_not_checked(self) -> None:
        found = scan_sections(
            ScanInput(language="en", sections=(_section(self.ENGLISH, None),))
        )
        assert found.english_sections == ()

    def test_an_untitled_section_is_named_by_position(self) -> None:
        found = scan_sections(
            ScanInput(language="pt", sections=(_section(self.ENGLISH, None),))
        )
        assert found.english_sections == ("#1",)
