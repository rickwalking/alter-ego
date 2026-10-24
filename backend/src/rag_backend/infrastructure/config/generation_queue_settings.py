"""The generation worker settings (ADR-0026).

A mixin of ``Settings``, split out to keep ``settings.py`` under 400 lines.
``GENERATION_WORKER_CONCURRENCY`` is how many carousels generate at a time
(Pedro: 1); the worker's own DB pool stays small so the web pool is never starved.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

DEFAULT_WORKER_CONCURRENCY = 1
DEFAULT_WORKER_DB_POOL_SIZE = 3
DEFAULT_WORKER_DB_MAX_OVERFLOW = 2
ALIVE_FILE_NAME = "generation-worker.alive"
DEFAULT_WORKER_ALIVE_FILE = str(Path(tempfile.gettempdir()) / ALIVE_FILE_NAME)


class GenerationQueueSettings(BaseSettings):
    """Concurrency and resources of the generation worker."""

    generation_worker_concurrency: int = Field(
        default=DEFAULT_WORKER_CONCURRENCY,
        ge=1,
        validation_alias=AliasChoices(
            "GENERATION_WORKER_CONCURRENCY", "generation_worker_concurrency"
        ),
    )
    generation_worker_db_pool_size: int = Field(
        default=DEFAULT_WORKER_DB_POOL_SIZE,
        ge=1,
        validation_alias=AliasChoices(
            "GENERATION_WORKER_DB_POOL_SIZE", "generation_worker_db_pool_size"
        ),
    )
    generation_worker_db_max_overflow: int = Field(
        default=DEFAULT_WORKER_DB_MAX_OVERFLOW,
        ge=0,
        validation_alias=AliasChoices(
            "GENERATION_WORKER_DB_MAX_OVERFLOW", "generation_worker_db_max_overflow"
        ),
    )
    generation_worker_alive_file: str = Field(
        default=DEFAULT_WORKER_ALIVE_FILE,
        validation_alias=AliasChoices(
            "GENERATION_WORKER_ALIVE_FILE", "generation_worker_alive_file"
        ),
    )


__all__ = ["GenerationQueueSettings"]
