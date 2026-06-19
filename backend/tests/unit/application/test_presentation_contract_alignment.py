"""Cross-layer drift tests for carousel presentation contract."""

from __future__ import annotations

import pytest
import yaml

from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
    render_presentation_policy_context,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
)
from rag_backend.domain.constants.runtime_skills import (
    get_runtime_skills_filesystem_root,
)

# AE-0246: runtime skills are co-located inside the backend package; resolve them
# through the canonical package-relative resolver instead of a repo-root walk.
_PIPELINE_ROOT = get_runtime_skills_filesystem_root() / "carousel-pipeline"
CONTRACT_YAML = _PIPELINE_ROOT / "contracts" / "hero_lower_third_v1.yaml"
CONTENT_CONTRACTS = _PIPELINE_ROOT / "_shared" / "content-contracts.md"
TEXT_FORMATTING = _PIPELINE_ROOT / "_shared" / "text-formatting.md"


@pytest.mark.unit
class TestPresentationContractAlignment:
    """Gherkin: Runtime documentation drifts from canonical policy."""

    def test_yaml_slide_count_matches_typed_policy(self) -> None:
        raw = yaml.safe_load(CONTRACT_YAML.read_text(encoding="utf-8"))
        policy = load_presentation_policy(
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1
        )
        assert raw["slide_count"] == policy.slide_count

    def test_prompt_context_includes_policy_version_and_icons(self) -> None:
        policy = load_presentation_policy(
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1
        )
        context = render_presentation_policy_context(policy)
        assert policy.version in context
        for icon_name in policy.lucide_icon_allowlist:
            assert icon_name in context

    def test_shared_docs_reference_lucide_icon_name(self) -> None:
        contracts_text = CONTENT_CONTRACTS.read_text(encoding="utf-8")
        formatting_text = TEXT_FORMATTING.read_text(encoding="utf-8")
        assert "icon_name" in contracts_text
        assert "Lucide" in formatting_text or "lucide" in formatting_text.lower()
        assert "📝" not in contracts_text
