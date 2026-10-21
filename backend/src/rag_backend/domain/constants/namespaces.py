"""Retrieval namespace constants.

All Pinecone namespace names used across the retrieval layer.
Use these constants instead of string literals to prevent typos
and enable refactoring.
"""

NAMESPACE_PERSONAL = "personal"
NAMESPACE_PUBLIC = "public"
NAMESPACE_INTERNAL = "internal"

NAMESPACE_CAROUSEL = "carousel"

DEFAULT_KB_NAMESPACES: list[str] = [NAMESPACE_PERSONAL, NAMESPACE_PUBLIC]
