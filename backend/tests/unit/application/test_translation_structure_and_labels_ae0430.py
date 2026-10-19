"""AE-0430: EN keeps PT's structured shape; label scaffolding never reaches copy.

Gherkin: tests/features/content_gate_repair_ae0430.feature (sections C and E).
"""

from __future__ import annotations

import json
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from rag_backend.application.services.carousel.editorial_distribution_generation import (
    _generate_en_translations,
)
from rag_backend.application.services.carousel.editorial_translation_structure import (
    structured_source,
    structured_translation,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    build_presentation_review_updates,
)
from rag_backend.application.services.carousel.slide_scaffold_recovery import (
    split_scaffold_sections,
    strip_scaffold_labels,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_TRANSLATION_SHAPE_MISMATCH,
)
from tests.unit.application.content_gate_repair_fixtures_ae0430 import (
    POLICY_V4,
    load_fixture,
)

_TLDR_PT = "Grok Bot, reserva por telefone, agente com computador próprio"
_TLDR_EN = "Grok Bot, phone booking, agent with its own computer"
_ACTIONS_PT = [
    {"icon_name": "target", "title": "Escolha uma tarefa", "body": "Um comando claro."},
    {"icon_name": "eye", "title": "Acompanhe", "body": "Leia cada passo."},
]


def _intro_draft() -> dict[str, object]:
    return {
        "slide_index": 1,
        "slide_type": "intro",
        "title": "Viram o Grok Bot reservar mesa.",
        "draft_text": "A ligação chama atenção. O ponto real é o computador.",
        "tldr_strip": _TLDR_PT,
    }


def _llm(answer: dict[str, object]) -> MagicMock:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content=json.dumps(answer)))
    return llm


@pytest.mark.unit
@pytest.mark.asyncio
class TestTranslationKeepsShape:
    async def test_en_keeps_the_tldr_strip(self) -> None:
        """Scenario: EN keeps the TL;DR strip of the intro."""
        llm = _llm({
            "slides_en": [
                {
                    "slide_index": 1,
                    "heading": "They saw Grok Bot book a table.",
                    "body": "The call draws attention. The real point is the computer.",
                    "tldr_strip": _TLDR_EN,
                }
            ]
        })

        translations = await _generate_en_translations(llm, [_intro_draft()])

        prompt = llm.ainvoke.await_args.args[0][0].content
        assert f'"tldr_strip": "{_TLDR_PT}"' in prompt
        assert translations[1]["tldr_strip"] == _TLDR_EN
        review = build_presentation_review_updates(
            [_intro_draft()], translations_en=translations, policy_version=POLICY_V4
        )
        report = cast(dict[str, object], review["presentation_validation"])
        codes = [v["code"] for v in cast(list[dict[str, object]], report["violations"])]
        assert VIOLATION_TRANSLATION_SHAPE_MISMATCH not in codes

    async def test_missing_answer_falls_back_to_pt_shape(self) -> None:
        """Scenario: A translation that drops the TL;DR still has EN's TL;DR slot."""
        llm = _llm({"slides_en": [{"slide_index": 1, "heading": "H", "body": "B."}]})

        translations = await _generate_en_translations(llm, [_intro_draft()])

        assert translations[1]["tldr_strip"] == _TLDR_PT


@pytest.mark.unit
class TestStructuredTranslation:
    def test_source_carries_tldr_and_item_texts_only(self) -> None:
        """Scenario: The translation request carries the structured texts."""
        draft = {**_intro_draft(), "actions": _ACTIONS_PT, "content_kind": "features"}

        source = structured_source(draft)

        assert source == {
            "tldr_strip": _TLDR_PT,
            "actions": [
                {"title": "Escolha uma tarefa", "body": "Um comando claro."},
                {"title": "Acompanhe", "body": "Leia cada passo."},
            ],
        }
        assert structured_source({"tldr_strip": " ", "features": []}) == {}

    def test_items_translated_by_position_keep_icons(self) -> None:
        """Scenario: Item lists come back translated with the PT icons."""
        answer = {
            "actions": [
                {"title": "Pick a task", "body": "One clear command."},
                {"title": "", "body": "Read every step."},
            ]
        }
        draft = {"actions": _ACTIONS_PT, "content_kind": "features"}

        en = structured_translation(draft, answer)

        actions = cast(list[dict[str, object]], en["actions"])
        assert actions[0] == {
            "icon_name": "target",
            "title": "Pick a task",
            "body": "One clear command.",
        }
        assert actions[1]["title"] == "Acompanhe"
        assert actions[1]["body"] == "Read every step."
        assert en["content_kind"] == "features"
        assert _ACTIONS_PT[0]["title"] == "Escolha uma tarefa"

    def test_item_count_mismatch_keeps_pt_items(self) -> None:
        """Scenario: An answer with another item count keeps the PT shape."""
        en = structured_translation(
            {"actions": _ACTIONS_PT}, {"actions": [{"title": "Only one"}]}
        )
        assert en["actions"] == _ACTIONS_PT
        odd = structured_translation(
            {"actions": [*_ACTIONS_PT, "x"]}, {"actions": ["a", "b", "c"]}
        )
        assert odd["actions"] == [*_ACTIONS_PT, "x"]


@pytest.mark.unit
class TestLabelScaffoldStripped:
    def test_bold_locale_markers_are_sections(self) -> None:
        """Scenario: Bold locale markers are parsed as sections, not copy."""
        draft_text = cast(str, load_fixture()["slide_1_draft_text"])

        sections = split_scaffold_sections(draft_text)

        assert set(sections) == {"PT", "EN"}
        assert "**heading:** Everyone saw Grok Bot" in sections["EN"]
        assert strip_scaffold_labels("**PT**\n**body:** Texto.\n**EN:**") == "Texto."

    def test_prod_intro_draft_builds_clean_pt_and_en(self) -> None:
        """Scenario: Bold locale markers are parsed as sections, not copy (build)."""
        draft = {**_intro_draft(), "draft_text": load_fixture()["slide_1_draft_text"]}

        review = build_presentation_review_updates([draft], policy_version=POLICY_V4)

        slide = cast(list[dict[str, object]], review["localized_slides"])[0]
        pt = cast(dict[str, object], slide["presentation_pt"])
        en = cast(dict[str, object], slide["presentation_en"])
        assert str(pt["body"]).startswith("A ligação chama atenção.")
        assert "**PT**" not in str(pt["body"]) and "**body:**" not in str(pt["body"])
        assert "**EN**" not in str(pt["body"])
        assert en["heading"] == (
            "Everyone saw Grok Bot book a table. Nobody talked about the computer."
        )
        assert str(en["body"]).startswith("The call draws attention.")
