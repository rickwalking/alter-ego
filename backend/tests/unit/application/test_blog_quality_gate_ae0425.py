"""Blog quality gate: voice score, scan and the single rewrite (AE-0425).

Feature: backend/tests/features/blog_generate_ae0425.feature
"""

from __future__ import annotations

from rag_backend.application.services.blog.blog_quality_gate import (
    BlogQualityGate,
    GateCommand,
    QualityGateDeps,
    article_text,
)
from rag_backend.domain.models.blog_generation import DraftSection, RewriteRequest
from tests.blog_generation_fakes import FakeScorer, FakeWriter, brief, sections

REPEATED = "Eu repito esta frase longa sobre agentes de IA em duas seções diferentes."
ORACLE = (
    "QUARANTINE_ORACLE_7f3a is the English research intro that must never reach PT."
)


def _gate(writer: FakeWriter, scorer: FakeScorer) -> BlogQualityGate:
    return BlogQualityGate(QualityGateDeps(writer=writer, scorer=scorer))


async def test_score_under_70_is_rewritten_exactly_once() -> None:
    # Scenario: A body scoring under 70 is rewritten exactly once
    writer, scorer = FakeWriter(), FakeScorer(scores=[62.0, 64.0])
    gated = await _gate(writer, scorer).run(GateCommand("pt", sections(4), brief(4)))
    assert len(writer.rewrites) == 1
    assert len(writer.judgements) == 1
    assert gated.rewrite_passes == 1
    # The second score is stored even when it is still under the bar.
    assert gated.voice.overall == 64.0
    assert writer.rewrites[0].notes == writer.notes


async def test_score_at_or_above_70_is_not_rewritten() -> None:
    # Scenario: A body scoring at or above 70 is not rewritten
    writer, scorer = FakeWriter(), FakeScorer(scores=[82.0])
    gated = await _gate(writer, scorer).run(GateCommand("pt", sections(4), brief(4)))
    assert writer.rewrites == []
    assert writer.judgements == []
    assert gated.rewrite_passes == 0
    assert gated.voice.overall == 82.0


async def test_exactly_70_passes() -> None:
    writer = FakeWriter()
    gated = await _gate(writer, FakeScorer(scores=[70.0])).run(
        GateCommand("pt", sections(3), brief(3))
    )
    assert gated.rewrite_passes == 0


async def test_repetition_triggers_the_rewrite_even_with_a_good_score() -> None:
    # Scenario: Seeded repetition is detected (the affected section is rewritten once)
    repeated = (
        DraftSection(None, f"{REPEATED} Abertura."),
        DraftSection("Dois", f"Algo novo. {REPEATED}"),
    )

    def fixed(request: RewriteRequest) -> tuple[DraftSection, ...]:
        return (
            DraftSection(None, "Abertura nova."),
            DraftSection("Dois", "Algo novo."),
        )

    writer = FakeWriter(rewrite_to=fixed)
    gated = await _gate(writer, FakeScorer(scores=[90.0])).run(
        GateCommand("pt", repeated, brief(2))
    )
    assert writer.judgements[0].findings.repeated_sentences == (REPEATED,)
    assert len(writer.rewrites) == 1
    assert gated.findings.repeated_sentences == ()
    assert gated.sections[0].body_md == "Abertura nova."


async def test_rewrite_is_renormalized_to_the_slide_count() -> None:
    def too_many(request: RewriteRequest) -> tuple[DraftSection, ...]:
        return sections(5)

    writer = FakeWriter(rewrite_to=too_many)
    gated = await _gate(writer, FakeScorer(scores=[50.0, 75.0])).run(
        GateCommand("pt", sections(4), brief(4))
    )
    assert len(gated.sections) == 4


async def test_en_is_gated_with_the_same_checks() -> None:
    # Scenario: EN is gated with the same voice/repetition checks
    writer, scorer = FakeWriter(), FakeScorer(scores=[60.0, 72.0])
    en = (DraftSection(None, "In today's world everything is AI, honestly."),)
    gated = await _gate(writer, scorer).run(GateCommand("en", en, brief(1)))
    assert writer.judgements[0].findings.banned_phrases == ("in today's world",)
    assert writer.rewrites[0].language == "en"
    assert gated.rewrite_passes == 1
    assert gated.voice.overall == 72.0


async def test_pt_never_keeps_an_english_research_sentence() -> None:
    # Scenario: No English research text leaks into the PT sections
    leaked = (
        DraftSection(None, f"Uma frase minha em português sobre agentes. {ORACLE}"),
    )
    research = (f"Background. {ORACLE}",)
    gated = await _gate(FakeWriter(), FakeScorer()).run(
        GateCommand("pt", leaked, brief(1, research=research))
    )
    assert all("QUARANTINE_ORACLE_7f3a" not in s.body_md for s in gated.sections)


async def test_en_keeps_the_research_material() -> None:
    # Scenario: ... translations.en contains the seeded material (not vacuous)
    english = (DraftSection(None, f"My own take on agents. {ORACLE}"),)
    gated = await _gate(FakeWriter(), FakeScorer()).run(
        GateCommand("en", english, brief(1, research=(ORACLE,)))
    )
    assert "QUARANTINE_ORACLE_7f3a" in gated.sections[0].body_md


def test_article_text_joins_headings_and_bodies() -> None:
    text = article_text((DraftSection(None, "Lede."), DraftSection("H", "Corpo.")))
    assert text == "Lede.\n\nH\n\nCorpo."
