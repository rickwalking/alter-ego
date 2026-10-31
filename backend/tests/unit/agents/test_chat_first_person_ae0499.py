"""The public chat speaks as Pedro, always in the first person.

Gherkin: tests/features/chat_first_person_ae0499.feature
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.prompts.registry import get_system_prompt
from rag_backend.domain.constants.alter_ego_prompt import (
    ALTER_EGO_PROMPT_NAME,
    ALTER_EGO_PROMPT_VERSION,
)
from tests.support.first_person_check import (
    is_first_person_reply,
    strip_lines,
    third_person_prompt_findings,
    third_person_reply_findings,
)

_FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "chat_first_person_eval.yaml"
)
_EVAL = yaml.safe_load(_FIXTURE.read_text(encoding="utf-8"))
_CASES: list[dict[str, str]] = _EVAL["cases"]
_CASE_IDS = [case["id"] for case in _CASES]
_EXTRA_BAD = [item["reply"] for item in _EVAL["extra_bad_replies"]]
_EXTRA_GOOD = [item["reply"] for item in _EVAL["extra_good_replies"]]
_REGISTRY = "rag_backend.agents.prompts.registry.get_system_prompt"
_RULE_HEADING = "SPEAKING AS YOURSELF (FIRST PERSON ONLY):"
_QUOTED_FORBIDDEN_LINES = (
    '- When referring to yourself, never use the third person: no "Pedro\'s", '
    '"Pedro is", "he", "his", "him", "o Pedro", "do Pedro", "ele", "dele". '
    "Talking about other people in the third person is fine.",
    '- NEVER call yourself "his alter ego", "his assistant", "an assistant for Pedro", '
    '"Pedro\'s assistant", "o alter ego dele" or "o assistente do Pedro". '
    'If someone asks who you are: "I\'m Pedro." / "Sou o Pedro."',
)


def _v4() -> str:
    """Load the v4 chat system prompt."""
    return get_system_prompt(ALTER_EGO_PROMPT_NAME, version=ALTER_EGO_PROMPT_VERSION)


class TestPromptVersion:
    """The agent loads v4; v3 stays loadable."""

    # Scenario: The chat agent loads the v4 prompt
    def test_agent_loads_the_v4_prompt(self) -> None:
        """The agent asks the registry for alter_ego at the v4 constant."""
        agent = AlterEgoAgent.__new__(AlterEgoAgent)
        with patch(_REGISTRY, return_value="loaded") as loader:
            assert agent._load_system_prompt() == "loaded"
        loader.assert_called_once_with("alter_ego", version="v4")

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
        """Apart from the two pinned quoted-phrase lines, v4 never uses the third person."""
        prompt = _v4()
        assert third_person_prompt_findings(prompt, _QUOTED_FORBIDDEN_LINES) == []
        assert "You are Pedro Marins" in strip_lines(prompt, _QUOTED_FORBIDDEN_LINES)

    # Scenario: The v4 prompt has no third-person reference to Pedro
    def test_v3_fails_the_same_scan(self) -> None:
        """The scan catches the v3 lines that leaked into replies."""
        prompt = get_system_prompt("alter_ego", version="v3")
        assert third_person_prompt_findings(prompt, ()).count("Pedro's") == 4

    # Scenario: The prompt scan skips only the pinned quoted-phrase lines
    def test_a_new_third_person_line_in_the_rule_section_is_caught(self) -> None:
        """Only the pinned lines are skipped, not the whole rule section."""
        prompt = _v4().replace(_RULE_HEADING, f"{_RULE_HEADING}\n- He keeps it short.")
        assert third_person_prompt_findings(prompt, _QUOTED_FORBIDDEN_LINES) == [
            "- He",
            "He",
        ]

    # Scenario: The v4 prompt states the first-person rule
    def test_v4_states_the_first_person_rule(self) -> None:
        """The rule section holds the pinned lines and the language rule."""
        prompt = _v4()
        section = prompt[prompt.index(_RULE_HEADING) :].split("\n\n")[0].splitlines()
        assert section[0] == _RULE_HEADING
        assert set(_QUOTED_FORBIDDEN_LINES) <= set(section)
        assert (
            "Talking about other people in the third person is fine."
            in _QUOTED_FORBIDDEN_LINES[0]
        )
        assert (
            "- Answer in the user's language (Portuguese or English), always in first person."
            in section
        )

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

    # Scenario: The v4 prompt keeps every v3 rule
    def test_v4_examples_are_well_formed(self) -> None:
        """Every example opens with a single bracket and is closed."""
        prompt = _v4()
        assert "<<example>" not in prompt
        assert prompt.count("<example>") == prompt.count("</example>") == 5


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

    # Scenario: Recorded third-person replies are flagged
    @pytest.mark.parametrize("reply", _EXTRA_BAD)
    def test_short_recorded_leak_is_flagged(self, reply: str) -> None:
        """Name-as-subject, "o Pedro", "his assistant" and pronoun-opening leaks are flagged."""
        assert not is_first_person_reply(reply)

    # Scenario: A reply that mentions someone else in the third person is not flagged
    @pytest.mark.parametrize("reply", _EXTRA_GOOD)
    def test_first_person_reply_about_someone_else_passes(self, reply: str) -> None:
        """A pronoun about a named someone else, or saying the own name, is not flagged."""
        assert third_person_reply_findings(reply) == []

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
            ("Sim. Pedro Marins gosta de RAG.", ". Pedro Marins gosta"),
            ("Sou o assistente dele.", "assistente dele"),
        ],
    )
    def test_named_phrases_are_reported(self, reply: str, expected: str) -> None:
        """The finding names the matched third-person phrase."""
        assert expected in third_person_reply_findings(reply)

    # Scenario: A reply that mentions someone else in the third person is not flagged
    def test_prompt_scan_counts_bare_pronouns(self) -> None:
        """The prompt scan flags bare pronouns that the reply check allows mid-reply."""
        text = "It is simple. He knows it and it is his."
        assert third_person_reply_findings(text) == []
        assert third_person_prompt_findings(text, ()) == ["He", "his"]

    # Scenario: The prompt scan skips only the pinned quoted-phrase lines
    def test_prompt_without_quoted_lines_is_scanned_whole(self) -> None:
        """No pinned lines means nothing is skipped."""
        prompt = "Use Pedro's CV.\n\nBe direct."
        assert strip_lines(prompt, ()) == prompt
        assert third_person_prompt_findings(prompt, ()) == ["Pedro's"]

    # Scenario: The prompt scan skips only the pinned quoted-phrase lines
    def test_a_missing_pinned_line_fails_the_scan(self) -> None:
        """A pinned quoted-phrase line that changed is reported, not silently skipped."""
        with pytest.raises(ValueError, match="never say"):
            third_person_prompt_findings("Be direct.", ("- never say his alter ego",))
