"""API-layer constants including error messages for HTTPException responses."""

from rag_backend.domain.constants import (
    COOKIE_ACCESS_TOKEN as COOKIE_ACCESS_TOKEN,
)  # re-export

# OpenAPI response descriptions (used in @router decorators)
ERR_NOT_AUTHENTICATED = "Not authenticated"
ERR_FORBIDDEN = "Forbidden"
ERR_NOT_FOUND = "Not found"

# Generic resource errors
ERR_ADMIN_REQUIRED = "Admin access required"
ERR_USER_NOT_FOUND = "User not found"
ERR_DOCUMENT_NOT_FOUND = "Document not found"
ERR_CONVERSATION_NOT_FOUND = "Conversation not found"
ERR_CAROUSEL_NOT_FOUND = "Carousel project not found"

# Carousel-specific errors
ERR_CAROUSEL_NOT_GENERATED = "Carousel not yet generated"
ERR_PDF_NOT_GENERATED = "PDF not yet generated"
ERR_PDF_FILE_MISSING = "PDF file missing on disk"
ERR_BLOG_NOT_GENERATED = "Blog post not yet generated"
ERR_DESIGN_NOT_GENERATED = "Design tokens not yet generated"
ERR_IMAGE_NOT_FOUND = "Image file not found"
ERR_OUTPUT_NOT_FOUND = "Output files not found"
ERR_INSTAGRAM_PUBLIC_BASE_URL_NOT_CONFIGURED = (
    "instagram_public_base_url_not_configured"
)
CAROUSEL_CACHE_HEADERS = {"Cache-Control": "public, max-age=31536000"}
CAROUSEL_PREVIEW_CACHE_HEADERS = {"Cache-Control": "private, no-store"}

# Media types
MEDIA_TYPE_JPEG = "image/jpeg"
MEDIA_TYPE_PDF = "application/pdf"
MEDIA_TYPE_STREAM = "text/event-stream"

# SSE event type constants
SSE_EVENT_TOKEN = "token"
SSE_EVENT_SOURCES = "sources"
SSE_EVENT_COMPLETE = "complete"
SSE_EVENT_ERROR = "error"
SSE_EVENT_TOOL_RESULT = "tool_result"
SSE_KEEP_ALIVE_INTERVAL_SECONDS = 15

# SSE validation / error messages
ERR_EMPTY_MESSAGE = "Message content cannot be empty"
ERR_NOT_CAROUSEL_CONVERSATION = "Not a carousel conversation"
