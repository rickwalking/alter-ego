"""Langfuse trace attributes for workflow phases.

Every editorial phase LLM call runs inside a trace named ``workflow_<phase>``
that carries the five metadata keys below and the three tags
``phase:<phase>``, ``agent:<agent_name>``, ``content:<content_type>``.

The agent and content-type defaults apply when no caller scope names them: the
HTTP editorial path has no agent of its own, and the autopilot overrides it with
``autopilot``. Langfuse rejects propagated metadata values longer than
``TRACE_METADATA_VALUE_MAX_CHARS``.
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
TRACE_NAME_REVIEW = "workflow_review"
TRACE_PHASE_REVIEW = "review"
TRACE_EVENT_HUMAN_REVIEW_TEMPLATE = "human_review_{phase}_completed"
TRACE_TAG_PHASE_TEMPLATE = "phase:{value}"
TRACE_TAG_AGENT_TEMPLATE = "agent:{value}"
TRACE_TAG_CONTENT_TEMPLATE = "content:{value}"

TRACE_STATUS_FIELD = "status"
TRACE_OUTPUT_STATUS_COMPLETED = "completed"
TRACE_OUTPUT_STATUS_ERROR = "error"
TRACE_ERROR_FIELD_TYPE = "error_type"
TRACE_ERROR_FIELD_MESSAGE = "error_message"
TRACE_DEFAULT_RUN_NAME = "llm.call"
TRACE_RUN_NAME_SEPARATOR = " "
TRACE_IO_VALUE_MAX_CHARS = 2000
TRACE_INPUT_TOPIC = "topic"
TRACE_OUTPUT_UPDATED_KEYS = "updated_keys"

TRACE_AGENT_EDITORIAL_WORKFLOW = "editorial_workflow"
TRACE_CONTENT_TYPE_CAROUSEL = "carousel"
TRACE_VALUE_UNKNOWN = "unknown"

TRACE_METADATA_VALUE_MAX_CHARS = 200

__all__ = [
    "TRACE_AGENT_EDITORIAL_WORKFLOW",
    "TRACE_CONTENT_TYPE_CAROUSEL",
    "TRACE_DEFAULT_RUN_NAME",
    "TRACE_ERROR_FIELD_MESSAGE",
    "TRACE_ERROR_FIELD_TYPE",
    "TRACE_EVENT_HUMAN_REVIEW_TEMPLATE",
    "TRACE_FIELD_AGENT_NAME",
    "TRACE_FIELD_CONTENT_TYPE",
    "TRACE_FIELD_PHASE",
    "TRACE_FIELD_PROJECT_ID",
    "TRACE_FIELD_USER_ID",
    "TRACE_INPUT_TOPIC",
    "TRACE_IO_VALUE_MAX_CHARS",
    "TRACE_METADATA_VALUE_MAX_CHARS",
    "TRACE_NAME_REVIEW",
    "TRACE_NAME_TEMPLATE",
    "TRACE_OUTPUT_STATUS_COMPLETED",
    "TRACE_OUTPUT_STATUS_ERROR",
    "TRACE_OUTPUT_UPDATED_KEYS",
    "TRACE_PHASE_REVIEW",
    "TRACE_REQUIRED_FIELDS",
    "TRACE_RUN_NAME_SEPARATOR",
    "TRACE_STATUS_FIELD",
    "TRACE_TAG_AGENT_TEMPLATE",
    "TRACE_TAG_CONTENT_TEMPLATE",
    "TRACE_TAG_PHASE_TEMPLATE",
    "TRACE_VALUE_UNKNOWN",
]
