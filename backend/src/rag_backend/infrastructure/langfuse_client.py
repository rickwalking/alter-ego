"""LangFuse client initialization and management."""

from langfuse import Langfuse

from rag_backend.infrastructure.config.settings import get_settings

LANGFUSE_CLIENT: Langfuse | None = None


def init_langfuse(
    public_key: str | None, secret_key: str, host: str
) -> Langfuse | None:
    """Initialize LangFuse tracing.

    Returns None if not configured.
    """
    global LANGFUSE_CLIENT
    if not public_key and not secret_key:
        LANGFUSE_CLIENT = None
        return None
    try:
        LANGFUSE_CLIENT = Langfuse(
            public_key=public_key or "",
            secret_key=secret_key,
            base_url=host,
        )
        from rag_backend import monitoring_langfuse as root_monitoring

        root_monitoring.init_langfuse(
            public_key or "",
            secret_key,
            host,
        )
        return LANGFUSE_CLIENT
    except ImportError:
        LANGFUSE_CLIENT = None
        return None


def get_langfuse_client() -> Langfuse | None:
    """Get the LangFuse client.

    Returns:
        LangFuse client instance or None
    """
    global LANGFUSE_CLIENT
    if LANGFUSE_CLIENT is None:
        settings = get_settings()
        LANGFUSE_CLIENT = init_langfuse(
            settings.langfuse_public_key,
            (
                settings.langfuse_secret_key.get_secret_value()
                if settings.langfuse_secret_key
                else ""
            ),
            settings.langfuse_host,
        )
    return LANGFUSE_CLIENT
