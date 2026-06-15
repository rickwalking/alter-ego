"""Application layer for the knowledge bounded context (private to the module).

Holds the use-case entry point (``KnowledgeService``) and owns the
Unit-of-Work boundary per request/command (ADR-0009 §4). Cross-module
consumers use the module facade, not this subpackage.
"""

from rag_backend.modules.knowledge.application.service import KnowledgeService

__all__ = ["KnowledgeService"]
