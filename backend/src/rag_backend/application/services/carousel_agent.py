"""Carousel agent.

DEPRECATED: Moved to `rag_backend.agents.carousel_orchestrator`.
This module re-exports for backward compatibility.
"""

from rag_backend.agents.carousel_orchestrator import CarouselAgent
from rag_backend.application.services.carousel.types import SlideData

__all__ = ["CarouselAgent", "SlideData"]
