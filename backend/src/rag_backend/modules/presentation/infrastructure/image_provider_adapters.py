"""Image-provider adapters for the presentation bounded context (AE-0119).

These are the infrastructure backing for the presentation image-generation
ports (``rag_backend.modules.presentation.domain.ports``):

* :class:`OpenAIImageService` / :class:`GeminiImageService` — the concrete vendor
  adapters that implement the :class:`ImageGenerationService` port. Each wraps a
  vendor SDK (``openai`` / ``google-genai``) behind the port so the carousel
  pipeline stays provider-agnostic.
* :class:`ImageProviderRegistry` — the concrete :class:`ImageProviderPort`: it
  resolves an ``(image_model, image_style)`` preset to a configured
  :class:`ImageProvider` (vendor service + style strategy).

**Re-export, not relocation (AE-0117/AE-0119 constraint).** The concrete vendor
services continue to live at ``rag_backend.infrastructure.external.openai_image``
/ ``...gemini_image`` and the registry at
``rag_backend.application.services.image_provider_registry``. This module merely
**re-exports** them under the presentation module's infrastructure namespace
(object-identity shims), so isinstance checks, the DI container wiring, and the
carousel image nodes keep resolving to the IDENTICAL objects — behavior is
byte-identical.

**Vendor SDK imports stay in the adapter/infrastructure layer.** This module
itself imports NO vendor SDK; the ``openai`` / ``google-genai`` imports live in
the wrapped ``infrastructure.external.*`` adapter classes. The presentation
APPLICATION/domain layers depend only on the ports, never on a vendor SDK.
"""

from __future__ import annotations

from rag_backend.application.services.image_provider_registry import (
    ImageProvider,
    ImageProviderRegistry,
)
from rag_backend.infrastructure.external.gemini_image import GeminiImageService
from rag_backend.infrastructure.external.openai_image import OpenAIImageService

__all__ = [
    "GeminiImageService",
    "ImageProvider",
    "ImageProviderRegistry",
    "OpenAIImageService",
]
