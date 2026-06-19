"""Shared Deep Agents harness — interrupt helpers (AE-0248).

Relocated from ``CarouselWorkflowEngine`` so the **generic** interrupt-value
extraction lives on the shared harness surface instead of being entangled (as a
classmethod) in the carousel engine. Behavior-preserving move: the body is
unchanged from the prior ``_iter_interrupt_values`` classmethod.

Only the carousel-agnostic primitive lives here. The review-payload merge that
knows the carousel state shape (``CarouselWorkflowState``) stays in the engine:
the harness must not import ``rag_backend.application`` (the ``agents → application``
edge is a down-only ratchet — only the grandfathered AE-0082 baseline imports are
allowed, and the harness is not one of them).
"""

from __future__ import annotations


def iter_interrupt_values(snapshot: object) -> list[dict[str, object]]:
    """Collect dict-valued payloads from a snapshot's pending interrupts."""
    payloads: list[dict[str, object]] = []
    for interrupt in getattr(snapshot, "interrupts", ()) or ():
        value = getattr(interrupt, "value", None)
        if isinstance(value, dict):
            payloads.append(value)
    for task in getattr(snapshot, "tasks", ()) or ():
        for interrupt in getattr(task, "interrupts", ()) or ():
            value = getattr(interrupt, "value", None)
            if isinstance(value, dict):
                payloads.append(value)
    return payloads


__all__ = ["iter_interrupt_values"]
