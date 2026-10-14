"""Failures a collector raises when an upstream has nothing usable to return."""

from __future__ import annotations


class UpstreamError(Exception):
    """The source failed. ``SignalsService`` records it and keeps the other sources."""
