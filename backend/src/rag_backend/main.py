"""Main entry point for the RAG backend application."""

import uvicorn

from rag_backend.api.app import create_app
from rag_backend.infrastructure.config.settings import get_settings

app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "rag_backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
