"""Golden-output parity tests for the AE-0243 prompt-registry migration.

Each test reconstructs the exact legacy inline f-string (the golden) and asserts
the registry-rendered prompt is byte-for-byte identical — proving the move from
inline f-strings to agents/prompts/**/*.yaml preserved behavior (whitespace,
ordering, and trailing-newline included). See AE-0243 arch-plan §12.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from rag_backend.agents import persona_agent
from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.agents.prompts.registry import PromptNotFoundError, render_prompt
from rag_backend.domain.models.persona import PersonaProfile


def test_persona_enforce_falls_back_when_registry_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Registry-unavailable path (AE-0243): the call site degrades to the 1-line
    # fallback instead of crashing.
    def _raise(*_a: object, **_k: object) -> tuple[str, dict[str, object]]:
        raise PromptNotFoundError("simulated missing prompt")

    monkeypatch.setattr(persona_agent, "render_prompt", _raise)
    agent = PersonaAgent(
        persona=PersonaProfile(
            name="Test Voice",
            description="Test persona",
            tone_attributes={"formal": 0.3},
            forbidden_phrases=[],
            preferred_phrases=[],
            writing_samples=[],
            expertise_areas=[],
        ),
        llm=AsyncMock(),
    )
    assert agent._build_style_guide() == persona_agent._ENFORCE_PROMPT_FALLBACK


def test_persona_enforce_parity() -> None:
    persona_name = "Pedro"
    tone_formal = 0.5
    tone_conversational = 0.5
    tone_humorous = 0.5
    sentence_structure = "short and punchy"
    paragraph_style = "white space"
    opinion_expression = "strong"
    forbidden = "- corporate speak\n- synergy"
    preferred = "- ship it"
    expertise = "AI, ML"
    samples = "- I built this in a weekend."

    legacy = f"""You are writing as {persona_name}.

TONE: formal={tone_formal}, conversational={tone_conversational}, humorous={tone_humorous}

SENTENCE STRUCTURE: {sentence_structure}

PARAGRAPH STYLE: {paragraph_style}

OPINION EXPRESSION: {opinion_expression}

FORBIDDEN PHRASES: {forbidden}

PREFERRED PHRASES: {preferred}

EXPERTISE AREAS: {expertise}

WRITING SAMPLES: {samples}

INSTRUCTION: Rewrite content to match this voice. Sound authentically human,
with strong opinions, personal anecdotes, zero generic AI-speak.
"""

    rendered, _ = render_prompt(
        "persona",
        "enforce",
        {
            "persona_name": persona_name,
            "tone_formal": tone_formal,
            "tone_conversational": tone_conversational,
            "tone_humorous": tone_humorous,
            "sentence_structure": sentence_structure,
            "paragraph_style": paragraph_style,
            "opinion_expression": opinion_expression,
            "forbidden_phrases": forbidden,
            "preferred_phrases": preferred,
            "expertise_areas": expertise,
            "writing_samples": samples,
        },
    )

    assert rendered == legacy


def test_quality_evaluate_parity() -> None:
    rubric_name = "Voice Rubric"
    rubric_description = "Checks voice match"
    applicable = "blog_post, carousel"
    criteria_str = "clarity: is it clear\ntone: does it match"
    content = "Some content here."
    sources_str = "src-1\nsrc-2"

    legacy = f"""Evaluate this content against the following quality rubric.

RUBRIC NAME: {rubric_name}
DESCRIPTION: {rubric_description}
APPLICABLE TO: {applicable}

CRITERIA:
{criteria_str}

CONTENT TO EVALUATE:
{content}

SOURCES USED:
{sources_str}

Format your response as JSON with criterion_scores, overall_score, passed, feedback.
"""

    rendered, _ = render_prompt(
        "quality",
        "evaluate",
        {
            "rubric_name": rubric_name,
            "rubric_description": rubric_description,
            "applicable_content_types": applicable,
            "criteria_str": criteria_str,
            "content": content,
            "sources_str": sources_str,
        },
    )

    assert rendered == legacy


def test_quality_improve_suggestions_parity() -> None:
    criterion_name = "clarity"
    criterion_description = "is it clear"
    score = 45.0
    threshold = 70
    content = "Some content here."

    legacy = f"""Generate 3-5 specific, actionable suggestions to improve this criterion.

CRITERION: {criterion_name}
DESCRIPTION: {criterion_description}
CURRENT SCORE: {score}/100
THRESHOLD: {threshold}/100

CONTENT: {content}
"""

    rendered, _ = render_prompt(
        "quality",
        "improve_suggestions",
        {
            "criterion_name": criterion_name,
            "criterion_description": criterion_description,
            "score": score,
            "threshold": threshold,
            "content": content,
        },
    )

    assert rendered == legacy


def test_quality_eeat_parity() -> None:
    content_preview = "Some content here, truncated to 500 chars."
    sources = ["src-1", "src-2"]

    legacy = f"""Evaluate E-E-A-T for content.

CONTENT: {content_preview}
SOURCES: {sources}

Format as JSON with experience, expertise, authoritativeness, trustworthiness, overall_eeat.
"""

    rendered, _ = render_prompt(
        "quality",
        "eeat",
        {"content_preview": content_preview, "sources": sources},
    )

    assert rendered == legacy


def test_linkedin_template_format_parity() -> None:
    # LinkedIn's prompt stays an inline guarded `_TEMPLATE` constant (it lives in
    # the `application` layer; see linkedin_post_generator for the DDD rationale).
    # This asserts the `.format()` template still produces the legacy output.
    from rag_backend.application.services import linkedin_post_generator as lpg

    result = lpg._build_prompt(
        lpg._PromptInput(
            blog="Blog body here.",
            language="en",
            title="My Topic",
            voice_examples="Sample voice line.",
        )
    )

    legacy = f"""You are writing a LinkedIn post in English from the blog
content below. Match the author's voice exactly.

Sample voice line.

Hard rules:
- Output the post body only. No labels, no markdown, no code fences.
- Plain text only — LinkedIn does not render markdown. Line breaks are
  fine. Bold and italics are not.
- First two lines must hook the reader (LinkedIn previews ~200 chars).
- {lpg.LINKEDIN_MAX_CHARS} character maximum including hashtags.
- End with 3-5 relevant hashtags on a final line.
- No em-dashes. Use commas or colons instead.
- No generic LinkedIn clichés ("Excited to share", "I am thrilled").
- Use short paragraphs (1-3 sentences).

Post topic: My Topic

Source blog (English):
<<<
Blog body here.
>>>

Write the LinkedIn post now."""

    assert result == legacy
