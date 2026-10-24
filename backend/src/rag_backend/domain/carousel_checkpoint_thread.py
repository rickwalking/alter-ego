"""The LangGraph checkpoint thread id of a carousel project.

The carousel workflow keys its checkpoints by the bare project id. The workflow
engine and the checkpoint prune both build the id here, so they cannot drift
apart again (the old cleanup job looked for a ``carousel-`` prefix that no
checkpoint ever carried).
"""

from __future__ import annotations


def checkpoint_thread_id(project_id: str) -> str:
    """Return the checkpoint ``thread_id`` of the carousel ``project_id``."""
    return project_id
