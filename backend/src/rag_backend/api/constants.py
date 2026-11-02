"""API-layer constants including error messages for HTTPException responses."""

from rag_backend.domain.constants import (
    COOKIE_ACCESS_TOKEN as COOKIE_ACCESS_TOKEN,
)

ERR_NOT_AUTHENTICATED = "Not authenticated"
ERR_INVALID_OR_EXPIRED_TOKEN = "Invalid or expired token"
WWW_AUTHENTICATE_BEARER = {"WWW-Authenticate": "Bearer"}
ERR_FORBIDDEN = "Forbidden"
ERR_NOT_FOUND = "Not found"
ERR_SEARCH_FAILED = "Search failed"
ERR_DOCUMENT_PROCESSING_FAILED = "Failed to process document"

ERR_ADMIN_REQUIRED = "Admin access required"
ERR_USER_NOT_FOUND = "User not found"
ERR_PASSWORD_CHANGE_REQUIRED = "Password change required"
ERR_DOCUMENT_NOT_FOUND = "Document not found"
ERR_CONVERSATION_NOT_FOUND = "Conversation not found"
ERR_CAROUSEL_NOT_FOUND = "Carousel project not found"

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

MEDIA_TYPE_JPEG = "image/jpeg"
MEDIA_TYPE_PDF = "application/pdf"
MEDIA_TYPE_STREAM = "text/event-stream"

ERR_NOT_CAROUSEL_CONVERSATION = "Not a carousel conversation"

ERR_CODE_USER_INACTIVE = "user_inactive"
ERR_CODE_PASSWORD_CHANGE_REQUIRED = "password_change_required"
ERR_CODE_CURRENT_PASSWORD_INCORRECT = "current_password_incorrect"
ERR_CODE_PASSWORD_UNCHANGED = "password_unchanged"
ERR_CODE_USER_EMAIL_EXISTS = "user_email_exists"
ERR_CODE_LAST_ADMIN = "last_admin"
ERR_CODE_SELF_DELETE = "self_delete"

ERR_LAST_ADMIN_DEMOTE = "Cannot demote the last admin"
ERR_LAST_ACTIVE_ADMIN_DEACTIVATE = "Cannot deactivate the last active admin"
