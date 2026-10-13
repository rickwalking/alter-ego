"""Inbound layer of the autopilot module.

Routes arrive in later tickets. This package holds the boundary DTOs those
adapters will return. Every future inbound adapter supplies an actor and
calls the context-owned authorization policy before the application service
(ADR-0009 §5).
"""
