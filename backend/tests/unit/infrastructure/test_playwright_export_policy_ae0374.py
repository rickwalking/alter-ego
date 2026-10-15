"""The export preflight checks a role deck against its own slide map (AE-0374).

Gherkin: tests/features/carousel_variable_slide_count.feature
"""

from __future__ import annotations

import pytest

from rag_backend.domain.protocols import ExportConfig
from rag_backend.infrastructure.external.playwright_export import export_policy


@pytest.mark.unit
class TestExportPolicy:
    def test_no_version_keeps_the_v1_map(self) -> None:
        policy = export_policy(ExportConfig())
        assert policy.version == "hero_lower_third_v1"
        assert policy.slide_count == 7

    def test_fixed_contract_keeps_the_v1_map(self) -> None:
        policy = export_policy(ExportConfig(policy_version="hero_lower_third_v3"))
        assert policy.version == "hero_lower_third_v1"

    @pytest.mark.parametrize("count", [8, 9, 10])
    def test_pov_deck_is_sized(self, count: int) -> None:
        policy = export_policy(
            ExportConfig(policy_version="pov_hook_v1", slide_count=count)
        )
        assert policy.slide_count == count
        assert policy.slides[-1].slide_type == "cta"
        assert policy.slides[-1].slide_number == count

    @pytest.mark.parametrize("count", [None, 3, 12])
    def test_missing_or_bad_count_uses_the_default(self, count: int | None) -> None:
        policy = export_policy(
            ExportConfig(policy_version="pov_hook_v1", slide_count=count)
        )
        assert policy.slide_count == 9
