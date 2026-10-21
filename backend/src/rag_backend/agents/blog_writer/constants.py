"""Constants of the blog writer agent (ADR-0025).

Prompt version v2 tells the judge, rewrite and draft prompts which language to keep. The
AGENT_* names are the JsonRetryPolicy.agent tags used in logs.
"""

from typing import Final

PROMPT_DOMAIN: Final = "blog"
PROMPT_VERSION: Final = "v2"
PROMPT_DRAFT: Final = "draft"
PROMPT_REWRITE: Final = "rewrite"
PROMPT_JUDGE: Final = "judge"

MAX_RESEARCH_ITEMS: Final = 12
MAX_RESEARCH_ITEM_CHARS: Final = 1_500
MAX_NOTE_CHARS: Final = 2_000
MAX_OUTLINE_ITEMS: Final = 12
MAX_SOURCE_URLS: Final = 10
MAX_PERSONA_SAMPLES: Final = 5
MAX_PERSONA_SAMPLE_CHARS: Final = 1_500
MAX_JUDGE_NOTES: Final = 8

KEY_TITLE: Final = "title"
KEY_SECTIONS: Final = "sections"
KEY_HEADING: Final = "heading"
KEY_BODY_MD: Final = "body_md"
KEY_EN: Final = "en"
KEY_NOTES: Final = "notes"

LANGUAGE_NAMES: Final[dict[str, str]] = {"pt": "Brazilian Portuguese", "en": "English"}
PERSONA_NONE: Final = "None"

AGENT_DRAFT: Final = "blog_writer_draft"
AGENT_REWRITE: Final = "blog_writer_rewrite"
AGENT_JUDGE: Final = "blog_writer_judge"
LOG_JUDGE_FAILED: Final = "blog_writer_judge_failed"
ERR_WRITER_FAILED: Final = "blog writer failed: {reason}"
ERR_SCORER_FAILED: Final = "blog voice scorer failed: {reason}"
ERR_BAD_ARTICLE: Final = "blog writer returned no usable sections"
