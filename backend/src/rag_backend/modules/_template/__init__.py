"""Reference template for a bounded-context module (AE-0081).

This package is the canonical skeleton every Phase 2+ bounded context copies
from. It demonstrates the module conventions documented in
``docs/architecture/module-conventions.md`` and ADR-0009 (Domain Modular
Monolith):

* per-module internal layers — ``domain/``, ``application/``,
  ``infrastructure/``, ``api/``;
* the **public-facade rule** — cross-module code imports ONLY from this
  package's public API (``public.py``, re-exported here); everything else is
  private to the module;
* manual constructor injection via ``bootstrap_module`` (no DI framework),
  per ADR-0009 §9;
* Unit-of-Work boundary owned at the application layer.

It is leading-underscore named (``_template``) so it is never mistaken for a
real bounded context and is excluded from any glob over real modules. It
carries no business logic.

Cross-module consumers SHALL import from the facade only::

    from rag_backend.modules._template import TemplateService, TemplateView

They SHALL NOT import module internals such as
``rag_backend.modules._template.application.service``.
"""

from rag_backend.modules._template.public import (
    TemplateService,
    TemplateView,
    bootstrap_module,
)

__all__ = [
    "TemplateService",
    "TemplateView",
    "bootstrap_module",
]
