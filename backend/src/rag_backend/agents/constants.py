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

# Error messages
ERR_JSON_PARSE = "Failed to parse evaluation response"

# AE-0407: a persona judge call that errors, times out or answers no usable
# overall is retried once; a second failure leaves the slide unscored.
PERSONA_JUDGE_CALLS = 2
PERSONA_JUDGE_TIMEOUT_SECONDS = 120.0
LOG_PERSONA_JUDGE_FAILED = "persona_judge_failed"
PERSONA_JUDGE_REASON_ERROR = "error"
PERSONA_JUDGE_REASON_NO_SCORE = "no_score"
