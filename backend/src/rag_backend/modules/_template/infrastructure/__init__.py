"""Infrastructure layer of the template module — port implementations.

The infrastructure layer implements the domain ports (database adapters,
external clients) and may depend on the platform substrate. It is wired into
the application layer by ``bootstrap_module``; nothing in domain/application
imports it directly (dependency inversion).

This layer is **private** to the module.
"""
