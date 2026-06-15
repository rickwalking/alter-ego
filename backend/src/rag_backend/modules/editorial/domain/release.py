"""Approval vs. public-release domain states for the editorial context.

This module formalizes the AE-0111 **contract split**: *approving* workflow
content and *making it public* are two DISTINCT concepts, expressed here as two
separate value objects, never conflated into one flag.

* :class:`ApprovalState` — derived from ``workflow_status``; ``is_approved`` is
  ``True`` exactly when ``workflow_status == approved_for_publish``. This is the
  workflow's statement that the content is ready to publish. It says **nothing**
  about visibility.
* :class:`PublicReleaseState` — derived from ``is_public``; ``is_public`` is the
  homepage/blog visibility flag. This says **nothing** about workflow approval.

The four combinations (approved/not by public/not) are all valid and independent.
This is a CONTRACT split only: it does NOT change who-can-see-what. The existing
publish routes stay the sole writer of ``is_public``, and the workflow engine
stays the sole writer of ``workflow_status``. No new status strings are
introduced — approval reuses the canonical
:data:`WORKFLOW_STATUS_APPROVED_FOR_PUBLISH` constant.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules.editorial.domain.status import (
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)


@dataclass(frozen=True)
class ApprovalState:
    """The content-approval state of a project (NOT its visibility).

    Built from the project's ``workflow_status``. ``is_approved`` is the single
    source of truth for "the workflow approved this content for publishing"; it
    is independent of :class:`PublicReleaseState`.
    """

    workflow_status: str

    @property
    def is_approved(self) -> bool:
        """``True`` iff ``workflow_status == approved_for_publish``."""
        return self.workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH

    @classmethod
    def from_workflow_status(cls, workflow_status: str | None) -> ApprovalState:
        """Build the approval state from a (possibly absent) ``workflow_status``."""
        return cls(workflow_status=workflow_status or "")


@dataclass(frozen=True)
class PublicReleaseState:
    """The public-release (visibility) state of a project (NOT its approval).

    Built from the project's ``is_public`` flag. ``is_public`` is the single
    source of truth for "this content is publicly visible"; it is independent of
    :class:`ApprovalState`.
    """

    is_public: bool

    @classmethod
    def from_is_public(cls, *, is_public: bool) -> PublicReleaseState:
        """Build the public-release state from the ``is_public`` flag."""
        return cls(is_public=bool(is_public))


__all__ = [
    "ApprovalState",
    "PublicReleaseState",
]
