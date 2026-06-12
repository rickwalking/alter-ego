"""Inbound (api) layer of the template module — inbound adapters and DTOs.

The api layer holds inbound adapters (HTTP routers, agent tools, workers,
event consumers) and the view/command DTOs that cross the module boundary.
Every inbound adapter supplies an ``ActorContext`` and calls the
context-owned authorization policy (ADR-0009 §5), and creates the
request-scoped Unit of Work passed into application services.

DTOs declared here (e.g. ``TemplateView``) are the only domain-shaped types
exposed through the public facade; the domain entities themselves stay
private.
"""
