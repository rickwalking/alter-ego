"""LangFuse observability integration."""

from langfuse.langchain import CallbackHandler

from rag_backend.infrastructure.config.settings import Settings

_langfuse_handler: CallbackHandler | None = None


def get_langfuse_handler() -> CallbackHandler | None:
    """Get the global LangFuse callback handler.

    Returns None if LangFuse was not initialized (not configured).
    """
    return _langfuse_handler


def init_langfuse(settings: Settings) -> CallbackHandler | None:
    """Initialize LangFuse tracing for LangChain call monitoring.

    Creates a LangChain-compatible callback handler that traces all
    LLM calls, chains, and agents through LangFuse. The handler is
    stored globally and can be retrieved via get_langfuse_handler().

    Returns None when LangFuse is not configured, allowing callers
    to skip LangFuse integration gracefully without conditional logic.
    """
    global _langfuse_handler

    if not settings.langfuse_secret_key:
        _langfuse_handler = None
        return None

    secret_key = settings.langfuse_secret_key.get_secret_value()
    if not secret_key:
        _langfuse_handler = None
        return None

    handler = CallbackHandler(
        secret_key=secret_key,
        public_key=settings.langfuse_public_key,
        host=settings.langfuse_host,
    )
    _langfuse_handler = handler
    return handler


def merge_callbacks(callbacks: list | None = None) -> list:
    """Append the LangFuse callback to an existing list.

    Convenience helper for services that construct their own
    LangChain callback lists. Returns a new list with the global
    LangFuse handler appended (or the original list if None).
    """
    handler = get_langfuse_handler()
    if handler is None:
        return callbacks or []
    return [*list(callbacks or []), handler]
