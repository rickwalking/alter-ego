"""Golden-output parity tests for the AE-0243 prompt-registry migration.

Each test reconstructs the exact legacy inline f-string (the golden) and asserts
the registry-rendered prompt is byte-for-byte identical — proving the move from
inline f-strings to agents/prompts/**/*.yaml preserved behavior (whitespace,
ordering, and trailing-newline included). See AE-0243 arch-plan §12.
"""

from __future__ import annotations

import pytest

from rag_backend.agents.prompts.registry import PromptNotFoundError, render_prompt
from rag_backend.application.services import linkedin_post_generator


def test_linkedin_prompt_falls_back_when_registry_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Registry-unavailable path (AE-0243): the call site degrades to the 1-line
    # fallback instead of crashing.
    def _raise(*_a: object, **_k: object) -> tuple[str, dict[str, object]]:
        raise PromptNotFoundError("simulated missing prompt")

    monkeypatch.setattr(linkedin_post_generator, "render_prompt", _raise)
    result = linkedin_post_generator._build_prompt(
        linkedin_post_generator._PromptInput(
            blog="b", language="en", title="t", voice_examples="v"
        )
    )
    assert result == linkedin_post_generator._LINKEDIN_PROMPT_FALLBACK


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


def test_distribution_linkedin_post_parity() -> None:
    lang_name = "English"
    voice_block = "Sample voice line."
    linkedin_max_chars = 3000
    title = "My Topic"
    blog = "Blog body here."

    legacy = f"""You are writing a LinkedIn post in {lang_name} from the blog
content below. Match the author's voice exactly.

{voice_block}

Hard rules:
- Output the post body only. No labels, no markdown, no code fences.
- Plain text only — LinkedIn does not render markdown. Line breaks are
  fine. Bold and italics are not.
- First two lines must hook the reader (LinkedIn previews ~200 chars).
- {linkedin_max_chars} character maximum including hashtags.
- End with 3-5 relevant hashtags on a final line.
- No em-dashes. Use commas or colons instead.
- No generic LinkedIn clichés ("Excited to share", "I am thrilled").
- Use short paragraphs (1-3 sentences).

Post topic: {title}

Source blog ({lang_name}):
<<<
{blog}
>>>

Write the LinkedIn post now."""

    rendered, _ = render_prompt(
        "distribution",
        "linkedin_post",
        {
            "lang_name": lang_name,
            "voice_block": voice_block,
            "linkedin_max_chars": linkedin_max_chars,
            "title": title,
            "blog": blog,
        },
    )

    assert rendered == legacy
