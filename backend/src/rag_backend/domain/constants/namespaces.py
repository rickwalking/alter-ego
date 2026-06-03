"""Retrieval namespace constants.

All Pinecone namespace names used across the retrieval layer.
Use these constants instead of string literals to prevent typos
and enable refactoring.
"""

# Knowledge-base namespaces
NAMESPACE_PERSONAL = "personal"
NAMESPACE_PUBLIC = "public"
NAMESPACE_INTERNAL = "internal"

# Content-pipeline namespace
NAMESPACE_CAROUSEL = "carousel"

# Default namespace sets for common queries
DEFAULT_KB_NAMESPACES: list[str] = [NAMESPACE_PERSONAL, NAMESPACE_PUBLIC]
