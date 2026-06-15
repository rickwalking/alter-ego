"""Module-level constants for the publishing bounded context.

Per backend/CLAUDE.md, each context owns its own ``constants`` file and no
magic strings appear in code. These constants identify the module for
tracing/observability metadata.

No new *domain* status/state strings are introduced here (AE-0126 constraint):
the blog workflow status language is re-exported (object-identity) from the
canonical :class:`~rag_backend.domain.constants.blog_post.BlogPostStatus`. Only
the module identity label lives here.
"""

# Module identity (used for tracing/observability metadata).
MODULE_NAME = "publishing"
