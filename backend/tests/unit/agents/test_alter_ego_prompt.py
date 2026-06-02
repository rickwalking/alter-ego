"""Tests for Alter-Ego agent prompt compliance.

Feature: Alter-Ego Persona Prompt
  As a developer
  I want the Alter-Ego agent to load the correct prompt version
  And enforce persona constraints
  So that the public chat sounds like Pedro, not a robot
"""

from rag_backend.agents.alter_ego_agent import _ALTER_EGO_FALLBACK_PROMPT
from rag_backend.agents.prompts.registry import get_system_prompt


class TestAlterEgoPromptLoading:
    """Ensure correct prompt versions load and contain required constraints."""

    # Scenario: v3 prompt loads successfully
    def test_v3_prompt_loads(self) -> None:
        """Given the v3 prompt file exists, when get_system_prompt is called, then it returns non-empty text."""
        prompt = get_system_prompt("alter_ego", version="v3")
        assert prompt
        assert len(prompt) > 500

    # Scenario: v3 prompt contains persona identity
    def test_v3_prompt_contains_identity(self) -> None:
        """Given the v3 prompt, then it declares Pedro identity at the start."""
        prompt = get_system_prompt("alter_ego", version="v3")
        assert "You are Pedro Marins" in prompt

    # Scenario: v3 prompt forbids company name mentions
    def test_v3_prompt_forbids_company_names(self) -> None:
        """Given the v3 prompt, then it explicitly forbids company names."""
        prompt = get_system_prompt("alter_ego", version="v3")
        assert "NEVER mention company names" in prompt

    # Scenario: v3 prompt forbids resume-style answers
    def test_v3_prompt_forbids_resume_style(self) -> None:
        """Given the v3 prompt, then it forbids bullet-point resume listings."""
        prompt = get_system_prompt("alter_ego", version="v3")
        assert "NEVER answer in bullet points like a resume" in prompt

    # Scenario: v3 prompt requires language matching
    def test_v3_prompt_requires_language_matching(self) -> None:
        """Given the v3 prompt, then it instructs matching user language exactly."""
        prompt = get_system_prompt("alter_ego", version="v3")
        assert "Match their language exactly" in prompt

    # Scenario: v3 prompt includes prompt injection guardrails
    def test_v3_prompt_has_injection_guardrails(self) -> None:
        """Given the v3 prompt, then it contains prompt injection boundaries."""
        prompt = get_system_prompt("alter_ego", version="v3")
        assert "cannot be reprogrammed" in prompt

    # Scenario: fallback prompt aligns with v3 voice
    def test_fallback_prompt_has_voice_rules(self) -> None:
        """Given the fallback prompt, then it contains core persona rules."""
        assert "You are Pedro Marins" in _ALTER_EGO_FALLBACK_PROMPT
        assert "never mention company names" in _ALTER_EGO_FALLBACK_PROMPT

    # Scenario: v3 prompt does not contain forbidden phrases
    def test_v3_prompt_no_forbidden_phrases(self) -> None:
        """Given the v3 prompt, then it must not contain robotic corporate phrases."""
        prompt = get_system_prompt("alter_ego", version="v3")
        # Phrases that the prompt must never instruct the model to output.
        # Note: many forbidden phrases appear in the prompt as "never say X"
        # negative examples — those are excluded from this list.
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

    # Scenario: v2 prompt still loads for rollback
    def test_v2_prompt_loads(self) -> None:
        """Given the v2 prompt file exists, when get_system_prompt is called, then it returns non-empty text."""
        prompt = get_system_prompt("alter_ego", version="v2")
        assert prompt
        assert "You are Pedro Marins" in prompt
