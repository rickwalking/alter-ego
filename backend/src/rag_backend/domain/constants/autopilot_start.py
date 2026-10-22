"""Spacing between autopilot generation starts (Pedro's decision).

The morning batch queues several runs within minutes; starting them back to back
stacks their Chromium exports and LLM calls on the 2 vCPU / 3.8 GB box. A queued
run starts only when the previous start is at least
``AUTOPILOT_START_SPACING_MINUTES`` old: 20 minutes by default, 0 turns the
spacing off.
"""

from __future__ import annotations

DEFAULT_START_SPACING_MINUTES = 20
