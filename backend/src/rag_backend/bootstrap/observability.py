"""Logging, tracing and Langfuse set-up shared by the web app and the worker."""

from __future__ import annotations

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.langfuse_client import init_langfuse
from rag_backend.infrastructure.logging import get_logger, setup_logging
from rag_backend.infrastructure.monitoring import init_langsmith
from rag_backend.infrastructure.telemetry.opentelemetry import init_opentelemetry

logger = get_logger()


def init_observability(settings: Settings) -> None:
    """Structured logs, LangSmith, OpenTelemetry and the Langfuse handler."""
    setup_logging(debug=settings.debug)
    init_langsmith(settings)
    init_opentelemetry(
        service_name=settings.otel_service_name,
        exporter_endpoint=settings.otel_exporter_endpoint,
        enabled=settings.otel_enabled,
    )
    langfuse_handler = init_langfuse(
        settings.langfuse_public_key,
        settings.langfuse_secret_key.get_secret_value()
        if settings.langfuse_secret_key
        else "",
        settings.langfuse_host,
    )
    if langfuse_handler:
        logger.info("langfuse_initialized", host=settings.langfuse_host)


__all__ = ["init_observability"]
