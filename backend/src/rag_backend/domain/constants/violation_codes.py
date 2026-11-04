"""The closed set of presentation rule ids, for safe diagnostics.

Every ``VIOLATION_*`` string in these modules is a rule id, so a new rule joins the
set on its own. Anything outside the set is free text and must not be stored.
"""

from __future__ import annotations

from typing import Final

from rag_backend.domain.constants import (
    carousel_presentation,
    playwright_geometry,
    presentation_roles,
)

_CONSTANT_PREFIX: Final[str] = "VIOLATION_"

KNOWN_VIOLATION_CODES: Final[frozenset[str]] = frozenset(
    value
    for module in (carousel_presentation, presentation_roles, playwright_geometry)
    for name, value in vars(module).items()
    if name.startswith(_CONSTANT_PREFIX) and isinstance(value, str)
)

__all__ = ["KNOWN_VIOLATION_CODES"]
