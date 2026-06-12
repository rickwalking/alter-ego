"""Composition root for the Alter-Ego backend.

This package is the single place where the dependency-injection container is
constructed and the FastAPI application is assembled and wired. It is the only
location permitted to reach across all layers to build the object graph
(container assembly + app factory + lifespan wiring).

Per ADR-0009 (Domain Modular Monolith), dependency injection is **manual
constructor injection** and the composition root lives here in ``bootstrap/``.
Business logic (domain/application/infrastructure) does NOT live here — only
wiring.

See ``docs/decisions/0009-adopt-domain-modular-monolith.md`` §9.
"""
