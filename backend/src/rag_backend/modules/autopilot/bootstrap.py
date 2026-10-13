"""Composition root for the autopilot module — manual constructor injection.

The inbound edge creates the request-scoped session (the unit of work) and
passes it here. This module does not look up a global container (ADR-0009 §9).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.application.service import AutopilotService
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)


@dataclass(frozen=True, kw_only=True)
class AutopilotBootstrapDeps:
    """Request-scoped wiring supplied by the inbound edge."""

    session: AsyncSession


def bootstrap_module(deps: AutopilotBootstrapDeps) -> AutopilotService:
    """Wire the repository to the application service for this session."""
    return AutopilotService(SqlAlchemyAutopilotRepository(deps.session))
