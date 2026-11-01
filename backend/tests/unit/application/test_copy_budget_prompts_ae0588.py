"""The drafting and translation prompts state each field's contract limit.

Gherkin: tests/features/copy_fits_slide_budgets_ae0588.feature (section A).
Every number asserted here is read from the loaded contract, never retyped,
except where a test changes the contract on purpose.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from rag_backend.agents.content_draft_agent import _render_content_prompt
from rag_backend.application.services.carousel.copy_budget_limits import (
    field_limit,
    limits_payload,
    slide_field_limits,
)
from rag_backend.application.services.carousel.editorial_distribution_generation import (
    _build_translation_payload,
    _generate_en_translations,
)
from rag_backend.application.services.carousel.instruction_context_loader import (
    CarouselInstructionContextLoader,
    InstructionContextRequest,
    _limits_block,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    TextBudget,
)
from rag_backend.domain.constants.carousel import (
    CAROUSEL_PROMPT_VERSION_V10,
    CAROUSEL_TRANSLATION_PROMPT_VERSION,
)
from rag_backend.domain.constants.carousel_presentation import MIN_CONTENT_BODY_WORDS
from rag_backend.domain.constants.content_mode import HOOK_MAX_WORDS
from rag_backend.domain.constants.pov_prompts import (
    POV_NEWS_PROMPT_DOMAIN,
    POV_PROMPT_CONTENT_VERSION,
    POV_PROMPT_DOMAIN,
)
from rag_backend.domain.models.pov_prompts import (
    PovSlideContext,
    PovThesis,
    SlidePolicyContext,
)
from tests.unit.application.copy_budget_fit_fixtures_ae0588 import (
    POLICY_POV,
    POLICY_V4,
)

_ROLES = ("hook", "rehook", "pov", "point", "twist", "save", "cta")
_CHAR_COUNT = re.compile(r"\d+\s*(caracteres|characters|chars)", re.IGNORECASE)


def _instruction(slide_number: int) -> str:
    return CarouselInstructionContextLoader.load(
        InstructionContextRequest(
            phase="content",
            locale="pt",
            slide_number=slide_number,
            policy_version=POLICY_POV,
            slide_count=9,
        )
    ).instruction


def _pov_prompt(domain: str, role: str) -> str:
    variables: dict[str, object] = {
        "slide_number": 2,
        "title": "Revisões",
        "key_points": "dono, regra",
        "locale": "pt",
        "phase": "content",
        "presentation_policy_context": "",
        "persona_context": "",
        "quality_rubric": "",
    }
    policy = SlidePolicyContext(
        policy_version=POLICY_POV,
        slide_count=9,
        pov=PovSlideContext(
            pov=PovThesis(thesis="Revisão precisa de dono.", prompt_domain=domain),
            role=role,
            slide_count=9,
            hook_text="Revisão sem dono vira opinião",
            cta_copy="Salve este post.",
        ),
    )
    return _render_content_prompt(variables, policy)[0]


@pytest.mark.unit
class TestDraftingLimits:
    def test_content_slide_lists_the_validator_limits(self) -> None:
        """Scenario: The drafting instruction states this slide's field limits from the contract."""
        policy = load_presentation_policy(POLICY_POV)
        heading = policy.copy_budgets["content_heading"]
        body = policy.copy_budgets["content_body"]
        feature_title = policy.copy_budgets["feature_title"]
        feature_body = policy.copy_budgets["feature_body"]

        instruction = _instruction(3)

        assert "Copy limits of this slide (content)" in instruction
        assert (
            f"- heading: at most {heading.max_characters} characters, "
            f"at most {heading.max_lines} lines"
        ) in instruction
        assert (
            f"- body: at most {body.max_characters} characters, at most "
            f"{body.max_lines} lines, at least {MIN_CONTENT_BODY_WORDS} words"
        ) in instruction
        assert (
            f"- features[].title: at most {feature_title.max_characters} characters"
        ) in instruction
        assert (
            f"- features[].body: at most {feature_body.max_characters} characters"
        ) in instruction

    def test_changed_contract_value_changes_the_prompt(self) -> None:
        """Scenario: A changed contract value changes the prompt budget."""
        policy = load_presentation_policy(POLICY_POV)
        changed = replace(
            policy,
            copy_budgets={
                **policy.copy_budgets,
                "content_body": TextBudget(max_characters=123, max_lines=4),
            },
        )

        block = _limits_block("content", changed)
        limits = {
            limit.field: limit for limit in slide_field_limits("content", changed)
        }

        assert "- body: at most 123 characters, at most 4 lines" in block
        assert limits["body"].max_characters == 123
        assert "123" not in _limits_block("content", policy)

    def test_hook_heading_carries_the_word_limit(self) -> None:
        """Scenario: The hook slide limit carries the word limit the validator applies."""
        policy = load_presentation_policy(POLICY_POV)
        subtitle = policy.copy_budgets["intro_subtitle"]

        instruction = _instruction(1)
        limits = {limit.field: limit for limit in slide_field_limits("intro", policy)}

        assert f"at most {HOOK_MAX_WORDS} words" in instruction
        assert limits["heading"].max_words == HOOK_MAX_WORDS
        assert limits["body"].max_characters == subtitle.max_characters
        assert "- body: at most 40 characters, at most 1 line\n" in instruction

    def test_hook_word_limit_absent_when_the_contract_has_no_hook_rule(self) -> None:
        """Scenario: The hook slide limit carries the word limit the validator applies (v1)."""
        policy = load_presentation_policy("hero_lower_third_v1")

        limits = {limit.field: limit for limit in slide_field_limits("intro", policy)}

        assert limits["heading"].max_words is None

    def test_summary_and_closing_list_their_items(self) -> None:
        """Scenario: The drafting instruction states this slide's field limits (items)."""
        policy = load_presentation_policy(POLICY_V4)

        summary = [limit.field for limit in slide_field_limits("summary", policy)]
        closing = [limit.field for limit in slide_field_limits("closing", policy)]
        cta = [limit.field for limit in slide_field_limits("cta", policy)]

        assert summary == ["heading", "summary_points[].title", "summary_points[].body"]
        assert closing == ["heading", "actions[].title", "actions[].body"]
        assert cta == ["heading"]

    def test_field_limit_reads_item_paths_and_unknown_fields(self) -> None:
        """Scenario: Nested summary point bodies are shortened (limit lookup)."""
        policy = load_presentation_policy(POLICY_V4)
        payload: dict[str, object] = {"slide_type": "summary"}

        item = field_limit(payload, "summary_points[2].body", policy)

        assert item is not None
        assert (
            item.max_characters
            == policy.copy_budgets["summary_point_body"].max_characters
        )
        assert field_limit(payload, "tldr_strip", policy) is None
        assert field_limit(payload, "body", policy) is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestTranslationLimits:
    async def test_translation_request_carries_each_slide_limits(self) -> None:
        """Scenario: The translation request carries each slide's field limits."""
        drafts: list[dict[str, object]] = [
            {
                "slide_index": 2,
                "slide_type": "summary",
                "policy_version": POLICY_V4,
                "title": "Três hábitos de revisão",
                "draft_text": "Resumo do que muda.",
            },
            {
                "slide_index": 3,
                "slide_type": "content",
                "policy_version": POLICY_V4,
                "title": "Revisões precisam de um dono",
                "draft_text": "Eu vejo o time perder horas com revisões.",
            },
        ]
        llm = MagicMock()
        llm.ainvoke = AsyncMock(
            return_value=AIMessage(content=json.dumps({"slides_en": []}))
        )
        policy = load_presentation_policy(POLICY_V4)

        payload = _build_translation_payload(drafts)
        await _generate_en_translations(llm, drafts)
        prompt = str(llm.ainvoke.await_args.args[0][0].content)

        assert payload[0]["limits"] == limits_payload("summary", policy)
        assert payload[1]["limits"] == limits_payload("content", policy)
        limits = cast(list[dict[str, object]], payload[1]["limits"])
        assert (
            limits[1]["max_characters"]
            == policy.copy_budgets["content_body"].max_characters
        )
        assert '"limits"' in prompt
        assert "Every English text must fit its limit" in prompt
        assert CAROUSEL_TRANSLATION_PROMPT_VERSION == CAROUSEL_PROMPT_VERSION_V10


@pytest.mark.unit
class TestPovPromptsHaveNoOwnNumbers:
    @pytest.mark.parametrize("domain", [POV_PROMPT_DOMAIN, POV_NEWS_PROMPT_DOMAIN])
    @pytest.mark.parametrize("role", _ROLES)
    def test_no_character_count_outside_the_limits_block(
        self, domain: str, role: str
    ) -> None:
        """Scenario: The POV content prompts carry no hardcoded character numbers."""
        prompt = _pov_prompt(domain, role)

        assert POV_PROMPT_CONTENT_VERSION == "v3"
        assert _CHAR_COUNT.search(prompt) is None
        assert "Copy limits of this slide" in prompt
