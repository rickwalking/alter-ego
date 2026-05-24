"""Constants for OpenTelemetry instrumentation (MON-001)."""

OTEL_SERVICE_NAME_DEFAULT = "rag-backend"
OTEL_SPAN_WORKFLOW_EVENT = "workflow_event.emit"
OTEL_SPAN_BLOG_LIST = "blog_post.list"
OTEL_SPAN_QUALITY_CHECK = "quality.check"
OTEL_SPAN_EDITORIAL_AUDIT = "editorial_audit.emit"

ATTR_AGGREGATE_ID = "aggregate_id"
ATTR_AGGREGATE_TYPE = "aggregate_type"
ATTR_EVENT_TYPE = "event_type"
ATTR_USER_ID = "user_id"

__all__ = [
    "ATTR_AGGREGATE_ID",
    "ATTR_AGGREGATE_TYPE",
    "ATTR_EVENT_TYPE",
    "ATTR_USER_ID",
    "OTEL_SERVICE_NAME_DEFAULT",
    "OTEL_SPAN_BLOG_LIST",
    "OTEL_SPAN_EDITORIAL_AUDIT",
    "OTEL_SPAN_QUALITY_CHECK",
    "OTEL_SPAN_WORKFLOW_EVENT",
]
