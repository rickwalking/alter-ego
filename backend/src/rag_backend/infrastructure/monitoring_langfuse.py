"""LangFuse observability integration."""

import os

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from rag_backend.infrastructure.config.settings import Settings


_langfuse_handler: CallbackHandler | None = None


def get_langfuse_handler() -> CallbackHandler | None:
    return _langfuse_handler


def init_langfuse(settings: Settings) -> CallbackHandler | None:
    global _langfuse_handler

    if not settings.langfuse_secret_key:
        _langfuse_handler = None
        return None

    secret_key = settings.langfuse_secret_key.get_secret_value()
    if not secret_key:
        _langfuse_handler = None
        return None

    os.environ.setdefault("LANGFUSE_SECRET_KEY", secret_key)
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)

    Langfuse(
        secret_key=secret_key,
        public_key=settings.langfuse_public_key,
        host=settings.langfuse_host,
    )

    handler = CallbackHandler(public_key=settings.langfuse_public_key)
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
