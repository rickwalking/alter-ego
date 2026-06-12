"""Application layer of the template module — use cases and UoW boundary.

The application layer orchestrates domain logic, owns the **Unit-of-Work
boundary**, and depends only on the domain layer (its ports), never on
infrastructure or api. Concrete adapters are supplied by ``bootstrap_module``
through constructor injection; the request-scoped Unit of Work is created at
the inbound edge and passed in — never resolved from a global container
(ADR-0009 §9).

This layer is **private** to the module.
"""
