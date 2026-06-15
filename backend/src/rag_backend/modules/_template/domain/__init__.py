"""Domain layer of the template module — entities, value objects, ports.

The domain layer is the innermost layer: it depends on nothing outward
(no application, infrastructure, or api imports). Ports (Protocols) declared
here are implemented by the infrastructure layer and wired by
``bootstrap_module`` (dependency inversion).

This layer is **private** to the module. Cross-module code reaches it only
indirectly through the public facade's view/command types.
"""
