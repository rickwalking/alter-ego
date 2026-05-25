"""Constants for blog post AI assistance."""

SUGGESTION_TYPE_IMPROVE = "improve"
SUGGESTION_TYPE_SHORTEN = "shorten"
SUGGESTION_TYPE_EXPAND = "expand"
SUGGESTION_TYPE_ADD_OPINION = "add_opinion"

AI_ACTION_IMPROVE = SUGGESTION_TYPE_IMPROVE
AI_ACTION_SHORTEN = SUGGESTION_TYPE_SHORTEN
AI_ACTION_EXPAND = SUGGESTION_TYPE_EXPAND
AI_ACTION_ADD_OPINION = SUGGESTION_TYPE_ADD_OPINION

VALID_AI_ACTIONS: frozenset[str] = frozenset({
    AI_ACTION_IMPROVE,
    AI_ACTION_SHORTEN,
    AI_ACTION_EXPAND,
    AI_ACTION_ADD_OPINION,
})

PROMPT_AI_SUGGEST = """Suggest an improved version of the selected blog text.

ACTION: {action}
CONTEXT: {context}

TEXT:
{text}

Respond with JSON: suggested_text, explanation.
"""

PROMPT_AI_IMPROVE = """Rewrite the selected blog text.

ACTION: {action}
CONTEXT: {context}

TEXT:
{text}

Return only the rewritten text.
"""

ERR_INVALID_AI_ACTION = (
    "Invalid AI action. Must be one of: improve, shorten, expand, add_opinion"
)
ERR_BLOG_POST_NOT_FOUND = "Blog post not found: {post_id}"
ERR_IMAGE_GENERATION_FAILED = "Image generation failed: {reason}"
