"""LangFuse observability integration. Cross-cutting concern — no layer restrictions."""

import os

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

_langfuse_handler: CallbackHandler | None = None


def get_langfuse_handler() -> CallbackHandler | None:
    return _langfuse_handler


def init_langfuse(
    public_key: str,
    secret_key: str,
    host: str,
) -> CallbackHandler | None:
    global _langfuse_handler

    if not secret_key:
        _langfuse_handler = None
        return None

    os.environ.setdefault("LANGFUSE_SECRET_KEY", secret_key)
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", public_key)
    os.environ.setdefault("LANGFUSE_HOST", host)

    Langfuse(
        secret_key=secret_key,
        public_key=public_key,
        host=host,
    )

    handler = CallbackHandler(public_key=public_key)
    _langfuse_handler = handler
    return handler


def merge_callbacks(callbacks: list | None = None) -> list:
    handler = get_langfuse_handler()
    if handler is None:
        return callbacks or []
    return [*list(callbacks or []), handler]
