"""OpenTelemetry instrumentation setup (MON-001)."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from rag_backend.domain.constants.telemetry import OTEL_SERVICE_NAME_DEFAULT
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_tracer = None
_initialized = False


def init_opentelemetry(
    *,
    service_name: str = OTEL_SERVICE_NAME_DEFAULT,
    exporter_endpoint: str = "",
    enabled: bool = False,
) -> bool:
    """Initialize OpenTelemetry if enabled and dependencies are available."""
    global _tracer, _initialized
    if _initialized or not enabled or not exporter_endpoint:
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning("opentelemetry_not_installed", hint="pip install opentelemetry-sdk")
        return False

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=exporter_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)
    _initialized = True
    logger.info("opentelemetry_initialized", service=service_name, endpoint=exporter_endpoint)
    return True


def instrument_fastapi(app: object) -> None:
    """Instrument FastAPI app if OTel is active."""
    if not _initialized:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)  # type: ignore[arg-type]
    except ImportError:
        logger.warning("opentelemetry_fastapi_not_installed")


@contextmanager
def start_span(name: str, attributes: dict[str, str] | None = None) -> Generator[None, None, None]:
    """Start a span if tracing is enabled, otherwise no-op."""
    if _tracer is None:
        yield
        return
    with _tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield


__all__ = ["init_opentelemetry", "instrument_fastapi", "start_span"]
