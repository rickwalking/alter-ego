"""Constants shared across Phase 2 AI agents."""

PROMPT_SOURCE_SYNTHESIS = """Extract key points from the following source material.

TITLE: {title}
TYPE: {source_type}

CONTENT:
{content}

Respond with JSON: {{"key_points": ["point 1", "point 2"], "summary": "one paragraph"}}.
"""

PROMPT_OUTLINE_GENERATION = """Create a slide-by-slide outline for an Instagram carousel.

TOPIC: {topic}
AUDIENCE: {audience}
BRIEF: {brief}
SOURCES:
{sources}

You MUST return exactly 7 slides (no more, no fewer) in this order:
1. intro — hook; optional "tldr_strip" (max 20 words) summarizing the whole topic
2. summary — 3 narrative beats as key_points (story in three sentences)
3-5. content — deep dives (stats, quotes, or checklist-friendly points)
6. closing — actionable takeaways as key_points
7. cta — save/share invitation

Respond with a JSON array only:
[{{"slide_index": 1, "title": "...", "key_points": ["..."], "slide_type": "intro", "tldr_strip": "..."}}]
"""

PROMPT_EDITORIAL_SLIDE_TRANSLATIONS = """Translate carousel slide copy to English.

Input slides (PT):
{slides_json}

Return JSON only: {{"slides_en": [{{"slide_index": 1, "heading": "...", "body": "..."}}]}}
Use the same slide_index values. Translate heading and body only.
"""

PROMPT_EDITORIAL_CAPTION_FALLBACK = """Write an Instagram caption (max 2200 chars) for this carousel.

Title: {title}
Slide headings:
{headings}

Return plain text only (no JSON). Include 5-10 relevant hashtags at the end.
"""

PROMPT_CONTENT_DRAFT = """Draft carousel slide copy.

SLIDE: {slide_index}
TITLE: {title}
KEY POINTS: {key_points}
PERSONA CONTEXT: {persona_context}

Return JSON: {{"draft_text": "...", "confidence_score": 0.0-1.0, "sources_used": []}}
"""

MODEL_ID_DEFAULT = "default-llm"
RAG_AGENT_USER_ID = "rag-agent"
ERR_INVALID_JSON = "Invalid JSON response from LLM"
