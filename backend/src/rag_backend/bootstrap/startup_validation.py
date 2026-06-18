"""Startup hardening validations for the composition root.

These guards run during application startup (``lifespan``) and assert that a
production-like deployment is configured durably and completely:

* AE-0213 — the LangGraph carousel checkpointer uses a durable backend
  (not the in-memory saver) so workflow state survives restarts.

The checks live here (and not in ``application``/``api``) deliberately: they are
infrastructure-aware composition-root concerns. They read only ``Settings`` and
emit a structured log; production-like environments fail fast, dev/test do not.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

# --- AE-0213: durable checkpointer -----------------------------------------

# Non-durable carousel checkpoint backends: state does not survive a restart.
NON_DURABLE_CHECKPOINT_BACKENDS: frozenset[str] = frozenset({"memory", "disabled"})

EVENT_CHECKPOINT_NON_DURABLE = "startup_checkpoint_backend_non_durable"
HINT_CHECKPOINT_DURABLE = (
    "set CAROUSEL_CHECKPOINT_BACKEND=postgres and "
    "CAROUSEL_CHECKPOINT_POSTGRES_URL for durable workflow state"
)
_ERR_CHECKPOINT_NON_DURABLE = (
    "Non-durable carousel checkpoint backend {backend!r} is not allowed in a "
    "production-like environment ({environment!r}). " + HINT_CHECKPOINT_DURABLE
)


class StartupValidationError(RuntimeError):
    """Raised when a production-like deployment is misconfigured at startup."""


@dataclass(frozen=True)
class StartupValidationResult:
    """Outcome of a non-fatal startup guard run in dev/test.

    ``checkpoint_durable`` is ``False`` when the corresponding guard found a
    problem that was downgraded to a warning because the environment is not
    production-like.
    """

    checkpoint_durable: bool


def validate_checkpointer_durability(settings: Settings) -> bool:
    """AE-0213: guard against a non-durable checkpointer in production.

    Returns ``True`` when the backend is durable (or the environment tolerates a
    non-durable one). Raises :class:`StartupValidationError` for a non-durable
    backend in a production-like environment; warns (and returns ``False``) in
    dev/test.
    """
    backend = settings.carousel_checkpoint_backend.strip().lower()
    if backend not in NON_DURABLE_CHECKPOINT_BACKENDS:
        return True

    if settings.is_production_like:
        raise StartupValidationError(
            _ERR_CHECKPOINT_NON_DURABLE.format(
                backend=backend, environment=settings.environment
            )
        )

    logger.warning(
        EVENT_CHECKPOINT_NON_DURABLE,
        backend=backend,
        environment=settings.environment,
        hint=HINT_CHECKPOINT_DURABLE,
    )
    return False


def run_startup_validations(settings: Settings) -> StartupValidationResult:
    """Run all composition-root startup guards.

    Raises :class:`StartupValidationError` on the first fatal misconfiguration in
    a production-like environment. In dev/test, downgrades to warnings and
    reports which guards flagged a problem.
    """
    return StartupValidationResult(
        checkpoint_durable=validate_checkpointer_durability(settings),
    )
