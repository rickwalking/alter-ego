"""Inbound layer of the autopilot module.

``router`` mounts ``/autopilot`` behind the service API key. Boundary DTOs
live in ``views``. Every inbound adapter calls the context-owned
authorization policy before the application service (ADR-0009 §5).
"""
