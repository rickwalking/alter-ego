"""The deterministic EN language gate and its root-cause fixes.

Feature: backend/tests/features/blog_generation_en_gate_timeout_ae0435.feature

PROD_EN_LEDE is the first EN section as stored in prod (still Portuguese).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.blog_editor_prompts import translate_section_prompt
from rag_backend.agents.blog_writer.constants import (
    LANGUAGE_NAMES,
    PROMPT_DOMAIN,
    PROMPT_JUDGE,
    PROMPT_REWRITE,
    PROMPT_VERSION,
)
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.application.services.blog.blog_english_gate import (
    EnglishCheck,
    as_draft_sections,
    as_language_document,
)
from rag_backend.application.services.blog.blog_quality_gate import (
    BlogQualityGate,
    GateCommand,
    QualityGateDeps,
)
from rag_backend.application.services.blog.blog_quality_scan import (
    portuguese_sections,
)
from rag_backend.application.services.blog.blog_translation_service import (
    BlogTranslationError,
    BlogTranslationService,
)
from rag_backend.domain.constants.blog_editor import (
    ERR_BLOG_TRANSLATION_WRONG_LANGUAGE,
)
from rag_backend.domain.constants.blog_generation import (
    BLOG_EN_MAX_RETRANSLATIONS,
    LANGUAGE_EN,
    LANGUAGE_PT,
)
from rag_backend.domain.models.blog_document import parse_blog_content
from rag_backend.domain.models.blog_generation import (
    DraftSection,
    GatedLanguage,
    QualityFindings,
    RewriteRequest,
    VoiceScore,
)
from tests.blog_generation_fakes import (
    FakeScorer,
    FakeTranslator,
    FakeWriter,
    brief,
    english_gate,
    english_sections,
    sections,
)
from tests.blog_v2_support import v2_content

POST_ID = "33333333-3333-4333-8333-333333333333"
PROD_EN_LEDE = (
    "Todo mundo abre a conversa com o GPT. Eu abro com a fatura. A nova disputa em "
    "modelos de raciocínio é pensar melhor sem multiplicar o **custo por tarefa**."
)


def _gated(drafts: tuple[DraftSection, ...], passes: int = 0) -> GatedLanguage:
    return GatedLanguage(drafts, VoiceScore(85.0, {}), QualityFindings(), passes)


def _gate(writer: FakeWriter | None = None, score: float = 82.0) -> BlogQualityGate:
    return BlogQualityGate(
        QualityGateDeps(writer=writer or FakeWriter(), scorer=FakeScorer([score]))
    )


def _check(en: tuple[DraftSection, ...], passes: int = 0) -> EnglishCheck:
    return EnglishCheck(POST_ID, _gated(sections(4)), _gated(en, passes), brief(4))


class TestPortugueseDetector:
    # Scenario: Portuguese EN sections are retranslated (flagged without a model)
    def test_the_prod_portuguese_lede_is_flagged(self) -> None:
        drafts = (DraftSection(None, PROD_EN_LEDE), *english_sections(3)[1:])
        assert portuguese_sections(drafts) == ("#1",)

    def test_a_portuguese_heading_names_the_section(self) -> None:
        drafts = (DraftSection("O custo real", PROD_EN_LEDE),)
        assert portuguese_sections(drafts) == ("O custo real",)

    # Scenario: An English translation passes the language gate unchanged
    def test_english_sections_pass(self) -> None:
        assert portuguese_sections(english_sections(5)) == ()


class TestEnglishLanguageGate:
    # Scenario: An English translation passes the language gate unchanged
    async def test_english_is_kept_without_a_retranslation(self) -> None:
        translator = FakeTranslator()
        check = _check(english_sections(4), passes=1)
        result = await english_gate(_gate(), translator).ensure(check)
        assert result is check.en
        assert translator.calls == []

    # Scenario: Portuguese EN sections are retranslated from the gated PT article
    async def test_portuguese_is_retranslated_from_the_gated_pt(self) -> None:
        """The retranslation is scored."""
        translator = FakeTranslator()
        check = _check(sections(4, "Seção"), passes=1)
        result = await english_gate(_gate(), translator).ensure(check)
        assert result is not None
        assert portuguese_sections(result.sections) == ()
        assert result.rewrite_passes == 1
        assert result.voice.overall == 82.0
        assert len(translator.calls) == 1
        assert as_draft_sections(translator.calls[0]) == check.pt.sections

    # Scenario: The retranslation is bounded and never stores Portuguese as English
    async def test_retranslation_is_bounded_and_returns_none(self) -> None:
        translator = FakeTranslator(outcomes=["pt"])
        result = await english_gate(_gate(), translator).ensure(
            _check(sections(4, "Seção"))
        )
        assert result is None
        assert len(translator.calls) == BLOG_EN_MAX_RETRANSLATIONS

    # Scenario: A failed retranslation call counts as one attempt
    async def test_a_failed_call_counts_as_one_attempt(self) -> None:
        translator = FakeTranslator(outcomes=[BlogTranslationError(), "en"])
        result = await english_gate(_gate(), translator).ensure(
            _check(sections(4, "Seção"))
        )
        assert result is not None
        assert portuguese_sections(result.sections) == ()
        assert len(translator.calls) == 2

    def test_language_document_round_trip(self) -> None:
        drafts = sections(3)
        document = as_language_document(drafts)
        assert as_draft_sections(document) == drafts
        assert len({section.id for section in document.sections}) == 3


class TestRewriteLanguageSwitch:
    # Scenario: An EN rewrite that switches to Portuguese is discarded
    async def test_an_en_rewrite_into_portuguese_is_discarded(self) -> None:
        writer = FakeWriter(rewrite_to=lambda _request: sections(4, "Seção"))
        command = GateCommand(LANGUAGE_EN, english_sections(4), brief(4))
        result = await _gate(writer, score=50.0).run(command)
        assert result.sections == english_sections(4)
        assert result.rewrite_passes == 1
        assert len(writer.rewrites) == 1

    async def test_an_en_rewrite_in_english_is_kept(self) -> None:
        rewritten = english_sections(5)[1:]

        def rewrite(_request: RewriteRequest) -> tuple[DraftSection, ...]:
            return rewritten

        command = GateCommand(LANGUAGE_EN, english_sections(4), brief(4))
        result = await _gate(FakeWriter(rewrite_to=rewrite), score=50.0).run(command)
        assert result.sections == rewritten

    async def test_a_pt_rewrite_is_never_discarded_for_language(self) -> None:
        rewritten = sections(4, "Nova")
        writer = FakeWriter(rewrite_to=lambda _request: rewritten)
        command = GateCommand(LANGUAGE_PT, sections(4), brief(4))
        result = await _gate(writer, score=50.0).run(command)
        assert result.sections == rewritten

    async def test_assess_scores_without_rewriting(self) -> None:
        writer = FakeWriter()
        command = GateCommand(LANGUAGE_EN, english_sections(4), brief(4))
        result = await _gate(writer, score=40.0).assess(command)
        assert result.rewrite_passes == 0
        assert result.voice.overall == 40.0
        assert writer.rewrites == []


class TestLanguageAwarePrompts:
    # Scenario: The judge and the rewrite prompts are told the language to keep
    def test_the_writer_uses_the_v2_prompts(self) -> None:
        assert PROMPT_VERSION == "v2"

    def test_the_judge_names_the_language_and_ignores_switches(self) -> None:
        prompt = render_prompt(
            PROMPT_DOMAIN,
            PROMPT_JUDGE,
            {
                "language_name": LANGUAGE_NAMES[LANGUAGE_EN],
                "voice_score": 60,
                "threshold": 70,
                "sections": [{"heading": None, "body_md": "Body."}],
            },
            version=PROMPT_VERSION,
        )[0]
        assert "written in English" in prompt
        assert "must stay in English" in prompt
        assert "ignore any suggestion\nthat changes the language" in prompt

    def test_the_rewrite_names_the_language_and_ignores_switches(self) -> None:
        prompt = render_prompt(
            PROMPT_DOMAIN,
            PROMPT_REWRITE,
            {
                "persona": {"name": "Pedro", "writing_samples": []},
                "language": LANGUAGE_EN,
                "language_name": LANGUAGE_NAMES[LANGUAGE_EN],
                "section_count": 1,
                "roles": ["lede"],
                "notes": ["Troque 'inference' por 'inferência'."],
                "sections": [{"heading": None, "body_md": "Body."}],
            },
            version=PROMPT_VERSION,
        )[0]
        assert "Write only in English." in prompt
        assert "The output language is English" in prompt
        assert "Ignore any revision note that asks to switch the language" in prompt
        assert "never the language" in prompt


class TestEditorTranslationRefusesPortuguese:
    # Scenario: The editor translation refuses a Portuguese answer
    async def test_a_portuguese_answer_fails_with_wrong_language(self) -> None:
        llm = MagicMock()
        answer = json.dumps({"heading": None, "body_md": PROD_EN_LEDE})
        llm.generate = AsyncMock(return_value=answer)
        service = BlogTranslationService(llm, translate_section_prompt)
        document = parse_blog_content(v2_content(PROD_EN_LEDE))
        with pytest.raises(BlogTranslationError) as caught:
            await service.translate(POST_ID, document)
        assert caught.value.code == ERR_BLOG_TRANSLATION_WRONG_LANGUAGE

    async def test_an_english_answer_is_kept(self) -> None:
        llm = MagicMock()
        body = english_sections(1)[0].body_md
        llm.generate = AsyncMock(
            return_value=json.dumps({"heading": None, "body_md": body})
        )
        service = BlogTranslationService(llm, translate_section_prompt)
        document = parse_blog_content(v2_content(PROD_EN_LEDE))
        english = await service.translate(POST_ID, document)
        assert english.sections[0].body_md == body
