"""Access control and generic API error constants."""

ERR_ACCESS_DENIED_NOT_OWNER = "Access denied: not the resource owner"
ERR_CONVERSATION_ACCESS_DENIED = "You do not own this conversation"
ERR_INVALID_REQUEST = "Invalid request"
ERR_BLOG_VERSION_NOT_FOUND = "Version {version_number} not found"

__all__ = [
    "ERR_ACCESS_DENIED_NOT_OWNER",
    "ERR_BLOG_VERSION_NOT_FOUND",
    "ERR_CONVERSATION_ACCESS_DENIED",
    "ERR_INVALID_REQUEST",
]
