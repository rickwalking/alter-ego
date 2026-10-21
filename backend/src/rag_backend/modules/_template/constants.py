"""Module-level constants for the template bounded context.

Per backend/CLAUDE.md, each context owns its own ``constants`` file and no
magic strings appear in code. This template carries only illustrative
constants.

``MODULE_NAME`` feeds tracing/observability metadata once a real context copies
this template; ``STATUS_DRAFT`` is an illustrative default for the example
aggregate's status field.
"""

MODULE_NAME = "_template"

STATUS_DRAFT = "draft"
