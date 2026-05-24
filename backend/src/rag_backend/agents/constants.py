"""Constants for persona agent."""

# Evaluation score keys
KEY_TONE_MATCH = "tone_match"
KEY_SENTENCE_STRUCTURE = "sentence_structure_match"
KEY_OPINION_STRENGTH = "opinion_strength"
KEY_ORIGINALITY = "originality"
KEY_HUMAN_AUTHENTICITY = "human_authenticity"
KEY_OVERALL = "overall"
KEY_SUGGESTIONS = "suggestions"

# Default scores
DEFAULT_SCORE = 0.0
DEFAULT_SCORE_INT = 0
DEFAULT_CONFIDENCE = 0.5

# Evaluation thresholds
MIN_VOICE_SCORE = 60.0
TARGET_VOICE_SCORE = 80.0
MAX_ITERATIONS = 5

# Tone attribute keys
KEY_FORMAL = "formal"
KEY_CONVERSATIONAL = "conversational"
KEY_HUMOROUS = "humorous"

# Style guide sections
SECTION_TONE = "TONE"
SECTION_SENTENCE = "SENTENCE STRUCTURE"
SECTION_PARAGRAPH = "PARAGRAPH STYLE"
SECTION_OPINION = "OPINION EXPRESSION"
SECTION_FORBIDDEN = "FORBIDDEN PHRASES"
SECTION_PREFERRED = "PREFERRED PHRASES"
SECTION_EXPERTISE = "EXPERTISE AREAS"
SECTION_SAMPLES = "WRITING SAMPLES"
SECTION_INSTRUCTION = "INSTRUCTION"

# Prompt templates
TEMPLATE_ENFORCE = """You are helping rewrite content to match the following persona voice.

PERSONA NAME: {persona_name}

TONE ATTRIBUTES:
- Formality: {tone_formal} (0.0 = casual, 1.0 = formal)
- Conversational: {tone_conversational} (0.0 = formal, 1.0 = conversational)
- Humor: {tone_humorous} (0.0 = serious, 1.0 = humorous)

SENTENCE STRUCTURE: {sentence_structure}

PARAGRAPH STYLE: {paragraph_style}

OPINION EXPRESSION: {opinion_expression}

FORBIDDEN PHRASES (NEVER USE):
{forbidden_phrases}

PREFERRED PHRASES (USE WHERE APPROPRIATE):
{preferred_phrases}

EXPERTISE AREAS: {expertise_areas}

WRITING SAMPLES (examples of this voice):
{writing_samples}

INSTRUCTIONS:
1. Rewrite to match this persona's voice perfectly
2. Use strong opinions where appropriate
3. Add personal perspective when relevant
4. Avoid generic AI-speak
5. Never use forbidden phrases
6. Use preferred phrases naturally
7. Keep sentences punchy and varied
8. Create white space with short paragraphs
9. Sound authentically human

OUTPUT FORMAT:
- Provide ONLY the rewritten text
- Do not include explanations or commentary
"""

# Error messages
ERR_JSON_PARSE = "Failed to parse evaluation response"
