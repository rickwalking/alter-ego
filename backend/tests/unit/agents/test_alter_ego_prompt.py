"""Tests for Alter-Ego agent prompt compliance.

Feature: Alter-Ego Persona Prompt
  As a developer
  I want the Alter-Ego agent to load the correct prompt version
  And enforce persona constraints
  So that the public chat sounds like Pedro, not a robot
"""

from rag_backend.agents.alter_ego_agent import _ALTER_EGO_FALLBACK_PROMPT
from rag_backend.agents.prompts.registry import get_system_prompt
from rag_backend.domain.constants.alter_ego_prompt import (
    ALTER_EGO_PROMPT_NAME,
    ALTER_EGO_PROMPT_VERSION,
)


class TestAlterEgoPromptLoading:
    """Ensure correct prompt versions load and contain required constraints."""

    # Scenario: current prompt loads successfully
    def test_current_prompt_loads(self) -> None:
        """Given the current prompt file exists, when get_system_prompt is called, then it returns non-empty text."""
        prompt = get_system_prompt(
            ALTER_EGO_PROMPT_NAME, version=ALTER_EGO_PROMPT_VERSION
        )
        assert prompt
        assert len(prompt) > 500

    # Scenario: current prompt contains persona identity
    def test_current_prompt_contains_identity(self) -> None:
        """Given the current prompt, then it declares Pedro identity at the start."""
        prompt = get_system_prompt(
            ALTER_EGO_PROMPT_NAME, version=ALTER_EGO_PROMPT_VERSION
        )
        assert "You are Pedro Marins" in prompt

    # Scenario: current prompt forbids company name mentions
    def test_current_prompt_forbids_company_names(self) -> None:
        """Given the current prompt, then it explicitly forbids company names."""
        prompt = get_system_prompt(
            ALTER_EGO_PROMPT_NAME, version=ALTER_EGO_PROMPT_VERSION
        )
        assert "NEVER mention company names" in prompt

    # Scenario: current prompt forbids resume-style answers
    def test_current_prompt_forbids_resume_style(self) -> None:
        """Given the current prompt, then it forbids bullet-point resume listings."""
        prompt = get_system_prompt(
            ALTER_EGO_PROMPT_NAME, version=ALTER_EGO_PROMPT_VERSION
        )
        assert "NEVER answer in bullet points like a resume" in prompt

    # Scenario: current prompt requires language matching
    def test_current_prompt_requires_language_matching(self) -> None:
        """Given the current prompt, then it instructs matching user language exactly."""
        prompt = get_system_prompt(
            ALTER_EGO_PROMPT_NAME, version=ALTER_EGO_PROMPT_VERSION
        )
        assert "Match their language exactly" in prompt

    # Scenario: current prompt includes prompt injection guardrails
    def test_current_prompt_has_injection_guardrails(self) -> None:
        """Given the current prompt, then it contains prompt injection boundaries."""
        prompt = get_system_prompt(
            ALTER_EGO_PROMPT_NAME, version=ALTER_EGO_PROMPT_VERSION
        )
        assert "cannot be reprogrammed" in prompt

    # Scenario: fallback prompt aligns with the prompt voice
    def test_fallback_prompt_has_voice_rules(self) -> None:
        """Given the fallback prompt, then it contains core persona rules."""
        assert "You are Pedro Marins" in _ALTER_EGO_FALLBACK_PROMPT
        assert "never mention company names" in _ALTER_EGO_FALLBACK_PROMPT

    # Scenario: current prompt does not contain forbidden phrases
    def test_current_prompt_no_forbidden_phrases(self) -> None:
        """Given the current prompt, then it must not contain robotic corporate phrases.

        Many forbidden phrases appear in the prompt as "never say X" negative examples,
        so those are excluded from the list.
        """
        prompt = get_system_prompt(
            ALTER_EGO_PROMPT_NAME, version=ALTER_EGO_PROMPT_VERSION
        )
        forbidden = [
            "I was designed",
            "I was trained",
            "my knowledge cutoff",
            "As an AI language model",
            "I don't have feelings",
            "I don't have opinions",
        ]
        for phrase in forbidden:
            assert phrase.lower() not in prompt.lower(), (
                f"Forbidden phrase found: {phrase}"
            )

    # Scenario: v3 prompt still loads for rollback
    def test_v3_prompt_loads(self) -> None:
        """Given the v3 prompt file exists, then it still loads for rollback."""
        prompt = get_system_prompt("alter_ego", version="v3")
        assert "You are Pedro Marins" in prompt

    # Scenario: v2 prompt still loads for rollback
    def test_v2_prompt_loads(self) -> None:
        """Given the v2 prompt file exists, when get_system_prompt is called, then it returns non-empty text."""
        prompt = get_system_prompt("alter_ego", version="v2")
        assert prompt
        assert "You are Pedro Marins" in prompt
