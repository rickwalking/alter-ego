"""Module-level constants for the publishing bounded context.

Per backend/CLAUDE.md, each context owns its own ``constants`` file and no
magic strings appear in code. These constants identify the module for
tracing/observability metadata.

No new *domain* status/state strings are introduced here:
the blog workflow status language is re-exported (object-identity) from the
canonical :class:`~rag_backend.domain.constants.blog_post.BlogPostStatus`. Only
the module identity label lives here.

- The workflow-board phase columns, in display order, are the single source of truth for
  the read projection and the legacy ``workflow_board`` route alias, byte-identical to
  the legacy ``KANBAN_PHASES`` ending in ``PHASE_PUBLISHED``.
- Rejected projects get their own column after the phases; the cards keep their real
  phase.
- The Instagram Story announcing a new carousel post is rendered from the PT slide 1
  into the serving root and fetched by Meta from the public route. Pillow's bundled font
  has no arrow glyph and the slim image ships no system fonts, so the caption arrow is
  drawn as a shape. The Story size is Instagram's Story image limit.
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
    PHASE_STATUS_REJECTED,
)

MODULE_NAME = "publishing"

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

BOARD_COLUMN_REJECTED = PHASE_STATUS_REJECTED
BOARD_COLUMNS = [*BOARD_PHASES, BOARD_COLUMN_REJECTED]

STORY_IMAGE_FILENAME = "story_pt.jpg"
STORY_IMAGE_URL = "{base}/api/carousels/{project_id}/story-image/pt.jpg"
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
STORY_MAX_BYTES = 8 * 1024 * 1024
STORY_IMAGE_MODE = "RGB"
STORY_JPEG_FORMAT = "JPEG"
STORY_TEMP_SUFFIX = ".tmp"
STORY_SLIDE_NUMBER = 1
STORY_CAPTION_ANCHOR = "lm"
ERR_STORY_IMAGE_TOO_LARGE = "story_image_too_large"
