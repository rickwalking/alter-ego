"""Langfuse trace attributes for workflow phases (AE-0390).

Every editorial phase LLM call runs inside a trace named ``workflow_<phase>``
that carries the five metadata keys below and the three tags
``phase:<phase>``, ``agent:<agent_name>``, ``content:<content_type>``.
"""

TRACE_FIELD_PROJECT_ID = "project_id"
TRACE_FIELD_PHASE = "phase"
TRACE_FIELD_AGENT_NAME = "agent_name"
TRACE_FIELD_USER_ID = "user_id"
TRACE_FIELD_CONTENT_TYPE = "content_type"

TRACE_REQUIRED_FIELDS = (
    TRACE_FIELD_PROJECT_ID,
    TRACE_FIELD_PHASE,
    TRACE_FIELD_AGENT_NAME,
    TRACE_FIELD_USER_ID,
    TRACE_FIELD_CONTENT_TYPE,
)

TRACE_NAME_TEMPLATE = "workflow_{phase}"
TRACE_TAG_PHASE_TEMPLATE = "phase:{value}"
TRACE_TAG_AGENT_TEMPLATE = "agent:{value}"
TRACE_TAG_CONTENT_TEMPLATE = "content:{value}"

# Defaults when no caller scope names them. The HTTP editorial path has no
# agent of its own; the autopilot overrides it with ``autopilot``.
TRACE_AGENT_EDITORIAL_WORKFLOW = "editorial_workflow"
TRACE_CONTENT_TYPE_CAROUSEL = "carousel"
TRACE_VALUE_UNKNOWN = "unknown"

# Langfuse rejects propagated metadata values longer than this.
TRACE_METADATA_VALUE_MAX_CHARS = 200

__all__ = [
    "TRACE_AGENT_EDITORIAL_WORKFLOW",
    "TRACE_CONTENT_TYPE_CAROUSEL",
    "TRACE_FIELD_AGENT_NAME",
    "TRACE_FIELD_CONTENT_TYPE",
    "TRACE_FIELD_PHASE",
    "TRACE_FIELD_PROJECT_ID",
    "TRACE_FIELD_USER_ID",
    "TRACE_METADATA_VALUE_MAX_CHARS",
    "TRACE_NAME_TEMPLATE",
    "TRACE_REQUIRED_FIELDS",
    "TRACE_TAG_AGENT_TEMPLATE",
    "TRACE_TAG_CONTENT_TEMPLATE",
    "TRACE_TAG_PHASE_TEMPLATE",
    "TRACE_VALUE_UNKNOWN",
]
