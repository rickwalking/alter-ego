"""Inbound-adapter layer for the conversation bounded context (private).

This is where the HTTP/agent/worker inbound adapters live once the chat routes
and the streaming service move behind the facade (AE-0101/0102). Per ADR-0009
§5-6, every inbound adapter creates the request-scoped Unit of Work at this edge
and supplies an ``ActorContext`` to the context-owned, deny-by-default
authorization policy before invoking the application service or the agent
factory.

Phase 3 (AE-0100) ships only the module skeleton, the facade, the re-exported
repository ports, and the ``ChatAgentFactory`` port + adapter — no routes or
streaming move yet and no behavior changes. The routes, the SSE streaming
adapter, and the policy arrive in AE-0101/0102, at which point this package
gains the boundary-safe view DTOs and inbound adapters.
"""

__all__: list[str] = []
