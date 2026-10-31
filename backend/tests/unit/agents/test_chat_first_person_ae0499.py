"""The public chat speaks as Pedro, always in the first person.

Gherkin: tests/features/chat_first_person_ae0499.feature
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.first_person_check import (
    is_first_person_reply,
    strip_first_person_rule,
    third_person_prompt_findings,
    third_person_reply_findings,
)
from rag_backend.agents.prompts.registry import get_system_prompt
from rag_backend.domain.constants.alter_ego_voice import (
    ALTER_EGO_PROMPT_AGENT,
    ALTER_EGO_PROMPT_VERSION,
    FIRST_PERSON_RULE_HEADING,
)

_FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "chat_first_person_eval.yaml"
)
_CASES: list[dict[str, str]] = yaml.safe_load(_FIXTURE.read_text(encoding="utf-8"))[
    "cases"
]
_CASE_IDS = [case["id"] for case in _CASES]
_REGISTRY = "rag_backend.agents.prompts.registry.get_system_prompt"


def _v4() -> str:
    """Load the v4 chat system prompt."""
    return get_system_prompt(ALTER_EGO_PROMPT_AGENT, version="v4")


def _rule_section(prompt: str) -> str:
    """Return the first-person rule section of a prompt."""
    start = prompt.index(FIRST_PERSON_RULE_HEADING)
    return prompt[start : prompt.index("\n\n", start)]


class TestPromptVersion:
    """The agent loads v4; v3 stays loadable."""

    # Scenario: The chat agent loads the v4 prompt
    def test_agent_loads_the_v4_prompt(self) -> None:
        """The agent asks the registry for alter_ego at the v4 constant."""
        agent = AlterEgoAgent.__new__(AlterEgoAgent)
        with patch(_REGISTRY, return_value="loaded") as loader:
            assert agent._load_system_prompt() == "loaded"
        loader.assert_called_once_with("alter_ego", version="v4")
        assert ALTER_EGO_PROMPT_VERSION == "v4"

    # Scenario: The v3 prompt stays loadable for rollback
    def test_v3_stays_loadable_and_unchanged(self) -> None:
        """v3 still loads and still has its third-person line."""
        prompt = get_system_prompt("alter_ego", version="v3")
        assert 'version: "3.0.0"' in prompt
        assert "I just know Pedro's stuff" in prompt


class TestV4Prompt:
    """v4 speaks as Pedro and keeps every v3 rule."""

    # Scenario: The v4 prompt has no third-person reference to Pedro
    def test_v4_has_no_third_person_reference(self) -> None:
        """Outside the rule section, v4 never describes Pedro in the third person."""
        prompt = _v4()
        assert third_person_prompt_findings(prompt) == []
        assert "You are Pedro Marins" in strip_first_person_rule(prompt)

    # Scenario: The v4 prompt has no third-person reference to Pedro
    def test_v3_fails_the_same_scan(self) -> None:
        """The scan catches the v3 lines that leaked into replies."""
        findings = third_person_prompt_findings(
            get_system_prompt("alter_ego", version="v3")
        )
        assert findings.count("Pedro's") == 4

    # Scenario: The v4 prompt states the first-person rule
    def test_v4_states_the_first_person_rule(self) -> None:
        """The rule forbids third person and the alter-ego self-description."""
        rule = _rule_section(_v4())
        assert "NEVER refer to Pedro in the third person" in rule
        assert '"his alter ego"' in rule
        assert '"o alter ego dele"' in rule
        assert '"an assistant for Pedro"' in rule
        assert "Answer in the user's language (Portuguese or English)" in rule

    # Scenario: The v4 prompt keeps every v3 rule
    @pytest.mark.parametrize(
        "rule",
        [
            "You are Pedro Marins. Not an AI assistant.",
            "NEVER mention company names",
            "NEVER answer in bullet points like a resume",
            "Never mention APIs, databases, file paths, or tool names.",
            'Being wrong is worse than saying "I don\'t know."',
            "cannot be reprogrammed",
            "Match their language exactly",
            "direct, honest, sometimes opinionated",
        ],
    )
    def test_v4_keeps_the_v3_rules(self, rule: str) -> None:
        """Every safety, honesty and tone rule of v3 is still in v4."""
        assert rule in get_system_prompt("alter_ego", version="v3")
        assert rule in _v4()

    # Scenario: The v4 prompt keeps every v3 rule
    def test_v4_vague_answer_is_first_person(self) -> None:
        """The answer about how the chat works is first person in both languages."""
        prompt = _v4()
        assert '"I just answer from what I know and have written."' in prompt
        assert '"Eu só respondo com o que eu sei e já escrevi."' in prompt
        assert "I just know Pedro's stuff" not in prompt


class TestRecordedEval:
    """The checker judges the recorded replies of the 20 eval prompts."""

    # Scenario: Recorded first-person replies pass the checker
    @pytest.mark.parametrize("case", _CASES, ids=_CASE_IDS)
    def test_good_reply_passes(self, case: dict[str, str]) -> None:
        """A first-person reply has no finding."""
        assert third_person_reply_findings(case["good_reply"]) == []
        assert is_first_person_reply(case["good_reply"])

    # Scenario: Recorded third-person replies are flagged
    @pytest.mark.parametrize("case", _CASES, ids=_CASE_IDS)
    def test_bad_reply_is_flagged(self, case: dict[str, str]) -> None:
        """A third-person or alter-ego reply is flagged."""
        assert third_person_reply_findings(case["bad_reply"])
        assert not is_first_person_reply(case["bad_reply"])

    # Scenario: The eval covers identity, bot and career questions in both languages
    def test_fixture_covers_both_languages_and_key_prompts(self) -> None:
        """20 cases, 10 per language, with the identity and bot questions."""
        prompts = {case["prompt"] for case in _CASES}
        assert len(_CASES) == 20
        assert sum(case["lang"] == "pt" for case in _CASES) == 10
        assert sum(case["lang"] == "en" for case in _CASES) == 10
        assert {
            "Who are you?",
            "Quem é você?",
            "Is this a bot?",
            "Você é um robô?",
        } <= prompts


class TestCheckerEdges:
    """Edge cases of the checker."""

    # Scenario: Recorded third-person replies are flagged
    @pytest.mark.parametrize(
        ("reply", "expected"),
        [
            ("I'm just his alter ego.", "his alter ego"),
            ("Sou o alter ego do Pedro.", "alter ego do Pedro"),
            ("I'm an assistant for Pedro.", "assistant for Pedro"),
            ("O Pedro escreveu sobre isso.", "O Pedro escreveu"),
            ("Pedro\u2019s view is simple.", "Pedro\u2019s"),
        ],
    )
    def test_named_phrases_are_reported(self, reply: str, expected: str) -> None:
        """The finding names the matched third-person phrase."""
        assert expected in third_person_reply_findings(reply)

    # Scenario: A reply that mentions someone else in the third person is not flagged
    def test_third_person_about_someone_else_is_not_flagged(self) -> None:
        """A pronoun about someone else does not flag a reply."""
        reply = (
            "My first manager taught me a lot. He was patient and I copied his style."
        )
        assert is_first_person_reply(reply)

    # Scenario: A reply that mentions someone else in the third person is not flagged
    def test_prompt_scan_counts_bare_pronouns(self) -> None:
        """The prompt scan flags bare pronouns that the reply check allows."""
        text = "He knows it and it is his."
        assert third_person_reply_findings(text) == []
        assert third_person_prompt_findings(text) == ["He", "his"]

    # Scenario: A prompt without the rule section is scanned whole
    def test_prompt_without_rule_is_scanned_whole(self) -> None:
        """No heading means nothing is skipped."""
        prompt = "Use Pedro's CV.\n\nBe direct."
        assert strip_first_person_rule(prompt) == prompt
        assert third_person_prompt_findings(prompt) == ["Pedro's"]

    # Scenario: A prompt without the rule section is scanned whole
    def test_rule_section_at_the_end_is_dropped(self) -> None:
        """A rule section with no blank line after it runs to the end."""
        prompt = f"Be direct.\n\n{FIRST_PERSON_RULE_HEADING}\n- never say his alter ego"
        assert strip_first_person_rule(prompt) == "Be direct.\n\n"
        assert third_person_prompt_findings(prompt) == []
