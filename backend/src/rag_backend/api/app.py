"""Backward-compatibility shim for the FastAPI application factory.

The composition root (app factory, middleware/route/lifespan wiring) was
relocated to ``rag_backend.bootstrap.app_factory`` in AE-0080 (ADR-0009 §9).
This module re-exports the public surface so existing imports such as
``from rag_backend.api.app import create_app`` keep working unchanged. No
behavior, routes, or schemas change — wiring only moved package.
"""

from rag_backend.bootstrap.app_factory import (
    create_app,
    lifespan,
)

__all__ = ["create_app", "lifespan"]
