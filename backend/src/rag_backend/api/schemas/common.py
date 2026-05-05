"""Common Pydantic schemas (error, health)."""

from datetime import datetime

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict[str, object] | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    checks: dict[str, dict[str, str | int]]
