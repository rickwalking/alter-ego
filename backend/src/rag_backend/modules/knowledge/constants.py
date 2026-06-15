"""Module-level constants for the knowledge bounded context.

Per backend/CLAUDE.md, each context owns its own ``constants`` file and no
magic strings appear in code. These constants identify the module for
tracing/observability and centralize the messages the application layer emits.
"""

# Module identity (used for tracing/observability metadata).
MODULE_NAME = "knowledge"
