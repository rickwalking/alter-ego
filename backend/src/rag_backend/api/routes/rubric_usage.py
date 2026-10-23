"""The 409 body of a rubric delete refused because carousels use it.

The caller sees their own carousels (id and topic) and only a count of the
others; an admin sees every carousel.
"""

from __future__ import annotations

from rag_backend.domain.constants.carousel_rubric import ERR_RUBRIC_IN_USE
from rag_backend.modules.editorial.public import RubricUser


def rubric_in_use_detail(
    using: list[RubricUser], caller_id: str, is_admin: bool
) -> dict[str, object]:
    """``{code, carousels, other_carousels}`` for the caller."""
    visible = [u for u in using if is_admin or u.owner_id == caller_id]
    return {
        "code": ERR_RUBRIC_IN_USE,
        "carousels": [{"id": u.project_id, "topic": u.topic} for u in visible],
        "other_carousels": len(using) - len(visible),
    }


__all__ = ["rubric_in_use_detail"]
