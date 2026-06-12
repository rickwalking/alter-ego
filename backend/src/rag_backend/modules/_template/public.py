"""Public facade for the template bounded context.

**This file is the module's public API.** Cross-module code SHALL import only
the symbols re-exported here (also re-exported from the package ``__init__``);
everything else under ``rag_backend.modules._template.*`` is private to the
module.

The facade exposes:

* ``TemplateService`` — the application service (use case entry point);
* ``TemplateView`` — the boundary-safe view DTO;
* ``bootstrap_module`` — the composition root (manual constructor injection).

Consumers SHALL NOT import internals such as
``rag_backend.modules._template.application.service`` or
``rag_backend.modules._template.domain.models``. The Import Linter contract
(AE-0082) enforces this; see ``docs/architecture/module-conventions.md``.
"""

from rag_backend.modules._template.api.views import TemplateView
from rag_backend.modules._template.application.service import TemplateService
from rag_backend.modules._template.bootstrap import bootstrap_module

__all__ = [
    "TemplateService",
    "TemplateView",
    "bootstrap_module",
]
