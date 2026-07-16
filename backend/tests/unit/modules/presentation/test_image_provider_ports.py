"""Deterministic fake-provider tests for the presentation image ports (AE-0119).

Phase-5 behavior-preserving port extraction: the image-generation contracts
(:class:`ImageGenerationService`, :class:`ImageStyleStrategy`), the provider
value object (:class:`ImageProvider`), and the registry contract
(:class:`ImageProviderPort`) are exposed behind the presentation facade, with the
concrete vendor adapters (OpenAI / Gemini) + :class:`ImageProviderRegistry`
implementing them. These tests prove:

* the ports + adapters are **object-identity shims** of the canonical objects
  (no behavior change, no new types);
* the OpenAI / Gemini adapters structurally satisfy ``ImageGenerationService``;
* the :class:`ImageProviderRegistry` structurally satisfies
  ``ImageProviderPort`` and its ``resolve(model, style)`` behavior — the
  supported ``(model, style)`` combos and the resolved strategy per combo — is
  IDENTICAL to the pre-refactor registry;
* a deterministic fake provider (no live API key) drives the port end-to-end
  through the registry, writing fixed bytes to disk.

No live vendor SDK is called: the fake provider writes fixed bytes itself, so the
suite is hermetic (there is no OpenAI / Gemini key in this environment).

Behavior-preserving — Gherkin not applicable (see ticket AE-0119); verified by
this suite + mypy / lint-imports / the AE-0116 safety net.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rag_backend.domain.constants import (
    IMAGE_MODEL_GEMINI,
    IMAGE_MODEL_OPENAI,
    IMAGE_STYLE_CINEMATIC,
    IMAGE_STYLE_COMIC_NEON,
    IMAGE_STYLE_HYPERREAL,
    IMAGE_STYLE_NEO_ANIME,
    SUPPORTED_IMAGE_COMBOS,
)
from rag_backend.modules.presentation import (
    GeminiImageService,
    ImageGenerationService,
    ImageProvider,
    ImageProviderPort,
    ImageProviderRegistry,
    ImageStyleStrategy,
    OpenAIImageService,
)

_FAKE_PNG_BYTES = b"\x89PNG\r\n\x1a\n-deterministic-fixture-bytes"


class FakeImageService(ImageGenerationService):
    """Deterministic ``ImageGenerationService`` — no vendor SDK, no API key.

    Records every prompt it is asked to render and writes FIXED bytes to the
    requested path so the registry + adapter wiring can be exercised end-to-end
    without a live provider.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def generate_image(self, prompt: str, output_path: str) -> str:
        self.calls.append((prompt, output_path))
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_FAKE_PNG_BYTES)
        return output_path


def _registry() -> ImageProviderRegistry:
    return ImageProviderRegistry(
        gemini_service=FakeImageService(),
        openai_service=FakeImageService(),
    )


class TestPortShimIdentity:
    """Scenario: the image ports re-export the canonical objects (identity)."""

    def test_image_generation_service_is_identical_object(self) -> None:
        from rag_backend.domain.protocols.carousel import (
            ImageGenerationService as Canonical,
        )

        assert ImageGenerationService is Canonical

    def test_image_style_strategy_is_identical_object(self) -> None:
        from rag_backend.domain.protocols.carousel import (
            ImageStyleStrategy as Canonical,
        )

        assert ImageStyleStrategy is Canonical

    def test_image_provider_is_identical_object(self) -> None:
        from rag_backend.application.services.image_provider_registry import (
            ImageProvider as Canonical,
        )

        assert ImageProvider is Canonical

    def test_registry_is_identical_object(self) -> None:
        from rag_backend.application.services.image_provider_registry import (
            ImageProviderRegistry as Canonical,
        )

        assert ImageProviderRegistry is Canonical

    def test_openai_adapter_is_identical_object(self) -> None:
        from rag_backend.infrastructure.external.openai_image import (
            OpenAIImageService as Canonical,
        )

        assert OpenAIImageService is Canonical

    def test_gemini_adapter_is_identical_object(self) -> None:
        from rag_backend.infrastructure.external.gemini_image import (
            GeminiImageService as Canonical,
        )

        assert GeminiImageService is Canonical


class TestAdaptersImplementPort:
    """Scenario: vendor adapters satisfy the ImageGenerationService port.

    ``ImageGenerationService`` / ``ImageStyleStrategy`` are NOT runtime-checkable
    Protocols (canonical, unchanged), so conformance is asserted (a) statically
    via a typed binding mypy verifies structurally and (b) at runtime via the
    port surface, not ``isinstance`` against a non-runtime Protocol.
    """

    def test_openai_service_satisfies_the_port(self) -> None:
        service: ImageGenerationService = OpenAIImageService(api_key="")
        assert callable(service.generate_image)

    def test_gemini_service_satisfies_the_port(self) -> None:
        service: ImageGenerationService = GeminiImageService(api_key="")
        assert callable(service.generate_image)

    def test_fake_service_satisfies_the_port(self) -> None:
        service: ImageGenerationService = FakeImageService()
        assert callable(service.generate_image)


class TestRegistryImplementsPort:
    """Scenario: the registry satisfies the ImageProviderPort contract."""

    def test_registry_is_an_image_provider_port(self) -> None:
        # ImageProviderPort IS runtime-checkable (new port) — isinstance is valid.
        assert isinstance(_registry(), ImageProviderPort)

    def test_resolve_returns_image_provider(self) -> None:
        provider = _registry().resolve(IMAGE_MODEL_OPENAI, IMAGE_STYLE_COMIC_NEON)
        assert isinstance(provider, ImageProvider)
        service: ImageGenerationService = provider.service
        strategy: ImageStyleStrategy = provider.strategy
        assert callable(service.generate_image)
        assert callable(strategy.wrap)


class TestResolveBehaviorUnchanged:
    """Scenario: resolve(model, style) behavior is identical post-refactor."""

    @pytest.mark.parametrize(
        ("model", "style", "strategy_name"),
        [
            (IMAGE_MODEL_OPENAI, IMAGE_STYLE_COMIC_NEON, "OpenAIComicNeonStrategy"),
            (IMAGE_MODEL_OPENAI, IMAGE_STYLE_CINEMATIC, "OpenAICinematicStrategy"),
            (IMAGE_MODEL_OPENAI, IMAGE_STYLE_HYPERREAL, "OpenAIHyperrealStrategy"),
            (IMAGE_MODEL_OPENAI, IMAGE_STYLE_NEO_ANIME, "OpenAINeoAnimeStrategy"),
        ],
    )
    def test_each_supported_combo_resolves_to_expected_strategy(
        self,
        model: str,
        style: str,
        strategy_name: str,
    ) -> None:
        provider = _registry().resolve(model, style)
        assert type(provider.strategy).__name__ == strategy_name

    def test_resolvable_combos_match_supported_set(self) -> None:
        registry = _registry()
        for model, style in SUPPORTED_IMAGE_COMBOS:
            assert isinstance(registry.resolve(model, style), ImageProvider)

    def test_comic_neon_uses_injected_openai_service(self) -> None:
        # AE-0308: comic_neon re-routed to OpenAI — no gemini combo remains.
        gemini = FakeImageService()
        openai = FakeImageService()
        registry = ImageProviderRegistry(gemini_service=gemini, openai_service=openai)
        provider = registry.resolve(IMAGE_MODEL_OPENAI, IMAGE_STYLE_COMIC_NEON)
        assert provider.service is openai

    def test_openai_combos_use_injected_openai_service(self) -> None:
        gemini = FakeImageService()
        openai = FakeImageService()
        registry = ImageProviderRegistry(gemini_service=gemini, openai_service=openai)
        provider = registry.resolve(IMAGE_MODEL_OPENAI, IMAGE_STYLE_HYPERREAL)
        assert provider.service is openai

    def test_unsupported_combo_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="not supported"):
            _registry().resolve(IMAGE_MODEL_GEMINI, IMAGE_STYLE_CINEMATIC)

    def test_unknown_model_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="not supported"):
            _registry().resolve("dalle-3", IMAGE_STYLE_HYPERREAL)

    def test_unknown_style_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="not supported"):
            _registry().resolve(IMAGE_MODEL_OPENAI, "ukiyo_e")


class TestEndToEndThroughPort:
    """Scenario: a fake provider drives the port end-to-end (no live key)."""

    @pytest.mark.asyncio
    async def test_resolve_then_generate_writes_fixed_bytes(
        self,
        tmp_path: Path,
    ) -> None:
        openai = FakeImageService()
        registry: ImageProviderPort = ImageProviderRegistry(
            gemini_service=FakeImageService(),
            openai_service=openai,
        )
        provider = registry.resolve(IMAGE_MODEL_OPENAI, IMAGE_STYLE_COMIC_NEON)

        scene = "a hooded figure at a glowing terminal"
        theme = {"primary": "#0ff", "accent": "#f0f", "background": "#000"}
        final_prompt = provider.strategy.wrap(scene, theme)
        output_path = str(tmp_path / "images" / "slide_1.jpg")

        result = await provider.service.generate_image(final_prompt, output_path)

        assert result == output_path
        assert Path(output_path).read_bytes() == _FAKE_PNG_BYTES
        assert openai.calls == [(final_prompt, output_path)]
        # The style wrapper prepends directives; the user scene appears verbatim.
        assert scene in final_prompt
