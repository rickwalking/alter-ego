"""LangSmith monitoring integration."""

import os

from rag_backend.infrastructure.config.settings import Settings


def init_langsmith(settings: Settings) -> None:
    """Initialize LangSmith tracing for LangChain monitoring.

    Args:
        settings: Application settings containing LangSmith configuration.
    """
    if not settings.langsmith_api_key or not settings.langsmith_tracing:
        return

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
