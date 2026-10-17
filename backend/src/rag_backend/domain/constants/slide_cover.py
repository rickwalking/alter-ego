"""Constants for the GrokBot slide-1 cover (AE-0418, ADR-0024).

GrokBot uploads a cover through ``POST /api/autopilot/assets``; the owner may
switch slide 1 to it on Telegram. Two kinds: an ``ai_image`` renders
full-bleed under the title, a ``screenshot`` renders as a framed card with a
source credit. The upload codes below are the public contract
(``docs/architecture/grokbot-cover-asset.md``); never rename them.
"""

from __future__ import annotations

COVER_KIND_AI_IMAGE = "ai_image"
COVER_KIND_SCREENSHOT = "screenshot"
COVER_KINDS: frozenset[str] = frozenset({COVER_KIND_AI_IMAGE, COVER_KIND_SCREENSHOT})
COVER_KIND_MAX_CHARS = 16

# Upload rejection codes (contract §3).
ERR_COVER_ASSET_TOO_LARGE = "asset_too_large"
ERR_COVER_ASSET_TOO_SMALL = "asset_too_small"
ERR_COVER_ASSET_TYPE_UNSUPPORTED = "asset_type_unsupported"
ERR_COVER_ASSET_KIND_INVALID = "asset_kind_invalid"
ERR_COVER_ASSET_SOURCE_MISSING = "asset_source_missing"

# Image rules: an ai_image is centre-cropped to 4:5 and must then be at least
# 1080x1350 (it is scaled down to exactly that); a screenshot keeps its aspect
# and needs 600 px of width. Both share the creator-asset maxima.
COVER_AI_RATIO_WIDTH = 4
COVER_AI_RATIO_HEIGHT = 5
COVER_AI_MIN_WIDTH = 1080
COVER_AI_MIN_HEIGHT = 1350
COVER_SCREENSHOT_MIN_WIDTH = 600

# Render: a staged cover whose file is gone fails slide 1 loudly.
ERR_SLIDE_COVER_UNREADABLE = "slide_cover_unreadable"

# ``carousel_projects.slide_cover`` JSON keys.
SLIDE_COVER_KEY_ASSET_ID = "asset_id"
SLIDE_COVER_KEY_KIND = "kind"
SLIDE_COVER_KEY_STAGED_PATH = "staged_path"
SLIDE_COVER_KEY_CREDIT = "credit"

# Screenshot credit: ``@handle · X`` for an X post, otherwise the domain.
COVER_CREDIT_X_TEMPLATE = "@{handle} · X"
COVER_CREDIT_WWW_PREFIX = "www."

__all__ = [
    "COVER_AI_MIN_HEIGHT",
    "COVER_AI_MIN_WIDTH",
    "COVER_AI_RATIO_HEIGHT",
    "COVER_AI_RATIO_WIDTH",
    "COVER_CREDIT_WWW_PREFIX",
    "COVER_CREDIT_X_TEMPLATE",
    "COVER_KINDS",
    "COVER_KIND_AI_IMAGE",
    "COVER_KIND_MAX_CHARS",
    "COVER_KIND_SCREENSHOT",
    "COVER_SCREENSHOT_MIN_WIDTH",
    "ERR_COVER_ASSET_KIND_INVALID",
    "ERR_COVER_ASSET_SOURCE_MISSING",
    "ERR_COVER_ASSET_TOO_LARGE",
    "ERR_COVER_ASSET_TOO_SMALL",
    "ERR_COVER_ASSET_TYPE_UNSUPPORTED",
    "ERR_SLIDE_COVER_UNREADABLE",
    "SLIDE_COVER_KEY_ASSET_ID",
    "SLIDE_COVER_KEY_CREDIT",
    "SLIDE_COVER_KEY_KIND",
    "SLIDE_COVER_KEY_STAGED_PATH",
]
