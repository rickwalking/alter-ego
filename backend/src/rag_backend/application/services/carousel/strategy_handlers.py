"""Pydantic models for carousel strategy API responses."""

from uuid import UUID

from pydantic import BaseModel


class StrategyInfo(BaseModel):
    """Strategy metadata returned in list responses."""

    name: str
    display_name: str


class StrategyListResponse(BaseModel):
    """Response model for the list-strategies endpoint."""

    strategies: list[StrategyInfo]


class ApplyStrategyResponse(BaseModel):
    """Response model for the apply-strategy endpoint."""

    project_id: UUID
    strategy: str
    message: str
