"""AE-0317 review r1 (m9): the kill switch must actually gate the wiring.

Scenario: Enrichment disabled restores legacy behavior
(tests/features/research_enrichment.feature) — flag→wiring half.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rag_backend.api.routes.carousels import (
    editorial_workflow_routes_support as support,
)


def _fake_container(research_tool: MagicMock) -> MagicMock:
    container = MagicMock()
    container.research_tool.return_value = research_tool
    container.llm_service.return_value.chat_model = MagicMock()
    container.image_provider_registry.return_value = MagicMock()
    return container


def _fake_settings(*, enabled: bool) -> MagicMock:
    settings = MagicMock()
    settings.research_enrichment_enabled = enabled
    settings.redis_url = None
    return settings


@pytest.mark.unit
class TestResearchEnrichmentWiring:
    def _build(self, *, enabled: bool) -> tuple[MagicMock, object]:
        research_tool = MagicMock()
        request = MagicMock()
        request.app.state.carousel_checkpointer = None
        with (
            patch.object(
                support, "get_container", return_value=_fake_container(research_tool)
            ),
            patch.object(
                support, "get_settings", return_value=_fake_settings(enabled=enabled)
            ),
        ):
            service = support.build_editorial_workflow_service(request)
        return research_tool, service

    def test_enabled_flag_wires_the_research_tool(self) -> None:
        research_tool, service = self._build(enabled=True)
        assert service._research_tool is research_tool

    def test_disabled_flag_wires_none(self) -> None:
        _research_tool, service = self._build(enabled=False)
        assert service._research_tool is None
