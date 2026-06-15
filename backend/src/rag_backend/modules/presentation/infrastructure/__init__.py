"""Infrastructure layer for the presentation bounded context.

Private to the module. Concrete adapters (the presentation policy loader, the
slide-validation adapter, the persistence/ACL seam) arrive in later phases
(AE-0118/0119) behind the module facade; this phase is scaffolding only and
relocates nothing (behavior-preserving). The generic carousel persistence
adapter is NOT relocated; it remains at its legacy location and is supplied to
the module's ``bootstrap_module`` by the inbound edge as the re-exported
``CarouselRepository`` port.
"""
