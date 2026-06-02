"""Access control and generic API error constants."""

ERR_ACCESS_DENIED_NOT_OWNER = "Access denied: not the resource owner"
ERR_CONVERSATION_ACCESS_DENIED = "You do not own this conversation"
ERR_CAROUSEL_NOT_PUBLIC = "Carousel content is not published"
ERR_CAROUSEL_TOOL_ACCESS_DENIED = "Access denied: carousel project not accessible"
ERR_INVALID_REQUEST = "Invalid request"
ERR_BLOG_VERSION_NOT_FOUND = "Version {version_number} not found"
ERR_SOURCE_NOT_FOUND = "Source not found: {source_id}"

__all__ = [
    "ERR_ACCESS_DENIED_NOT_OWNER",
    "ERR_BLOG_VERSION_NOT_FOUND",
    "ERR_CAROUSEL_NOT_PUBLIC",
    "ERR_CAROUSEL_TOOL_ACCESS_DENIED",
    "ERR_CONVERSATION_ACCESS_DENIED",
    "ERR_INVALID_REQUEST",
    "ERR_SOURCE_NOT_FOUND",
]
