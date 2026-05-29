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

Respond with JSON array of slides:
[{{"slide_index": 1, "title": "...", "key_points": ["..."], "visual_direction": "..."}}]
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
