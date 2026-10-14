"""Module-level constants for the publishing bounded context.

Per backend/CLAUDE.md, each context owns its own ``constants`` file and no
magic strings appear in code. These constants identify the module for
tracing/observability metadata.

No new *domain* status/state strings are introduced here (AE-0126 constraint):
the blog workflow status language is re-exported (object-identity) from the
canonical :class:`~rag_backend.domain.constants.blog_post.BlogPostStatus`. Only
the module identity label lives here.
"""

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_BRIEF,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    PHASE_PUBLISHED,
    PHASE_RESEARCH,
)

# Module identity (used for tracing/observability metadata).
MODULE_NAME = "publishing"

# Workflow-board phase columns, in display order (AE-0131). Single source of
# truth for both the read projection (the column grouping/order) and the legacy
# ``workflow_board`` route alias — re-exported via the facade so the route no
# longer owns the carousel-phase ordering. Byte-identical to the legacy
# ``KANBAN_PHASES`` ending in ``PHASE_PUBLISHED``.
BOARD_PHASES = [
    PHASE_BRIEF,
    PHASE_RESEARCH,
    PHASE_OUTLINE,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_IMAGES,
    PHASE_FINAL_REVIEW,
    PHASE_PUBLISHED,
]

# AE-0369: the Instagram Story announcing a new carousel post. Rendered from the
# PT slide 1 into the serving root and fetched by Meta from the public route.
STORY_IMAGE_FILENAME = "story_pt.jpg"
STORY_IMAGE_URL = "{base}/api/carousels/{project_id}/story-image/pt.jpg"
# The caption text and its arrow. Pillow's bundled font has no arrow glyph and
# the slim image ships no system fonts, so the arrow is drawn as a shape.
STORY_CAPTION_TEXT = "Novo post no perfil"
STORY_CAPTION_ARROW = "\u2191"
STORY_CAPTION_PT = f"{STORY_CAPTION_TEXT} {STORY_CAPTION_ARROW}"
STORY_ARROW_GAP = 24
STORY_ARROW_WIDTH = 40
STORY_ARROW_HEIGHT = 52
STORY_ARROW_HEAD_HEIGHT = 24
STORY_ARROW_SHAFT_WIDTH = 12
STORY_WIDTH = 1080
STORY_HEIGHT = 1920
STORY_SLIDE_TOP = 380
STORY_CAPTION_CENTER_Y = 290
STORY_CAPTION_FONT_SIZE = 64
STORY_CAPTION_COLOR = (255, 255, 255)
STORY_BAND_COLOR = (0, 0, 0)
STORY_BAND_HEIGHT = 140
STORY_BAND_ALPHA = 0.55
STORY_BLUR_RADIUS = 30
STORY_BACKGROUND_DARKEN = 0.55
STORY_JPEG_QUALITIES = (90, 80, 70)
# Instagram's Story image limit.
STORY_MAX_BYTES = 8 * 1024 * 1024
STORY_IMAGE_MODE = "RGB"
STORY_JPEG_FORMAT = "JPEG"
STORY_TEMP_SUFFIX = ".tmp"
STORY_SLIDE_NUMBER = 1
# Pillow text anchor: left edge, vertical middle.
STORY_CAPTION_ANCHOR = "lm"
ERR_STORY_IMAGE_TOO_LARGE = "story_image_too_large"
