"""Cross-layer drift tests for carousel presentation contract."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
    render_presentation_policy_context,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
)

def _repo_root() -> Path:
    """Resolve repo root for both normal and mutmut contexts."""
    test_file = Path(__file__).resolve()
    candidate = test_file.parents[4]
    if candidate.joinpath("skills/runtime").is_dir():
        return candidate
    # Mutmut copies to backend/mutants/ — check parent directories
    cwd = Path.cwd()
    for path in (cwd, cwd.parent, cwd.parent.parent):
        if path.joinpath("skills/runtime").is_dir():
            return path
    raise FileNotFoundError(
        f"Could not find repo root with skills/runtime from {test_file} or {cwd}"
    )


REPO_ROOT = _repo_root()
CONTRACT_YAML = (
    REPO_ROOT
    / "skills/runtime/carousel-pipeline/contracts/hero_lower_third_v1.yaml"
)
CONTENT_CONTRACTS = (
    REPO_ROOT / "skills/runtime/carousel-pipeline/_shared/content-contracts.md"
)
TEXT_FORMATTING = (
    REPO_ROOT / "skills/runtime/carousel-pipeline/_shared/text-formatting.md"
)


@pytest.mark.unit
class TestPresentationContractAlignment:
    """Gherkin: Runtime documentation drifts from canonical policy."""

    def test_yaml_slide_count_matches_typed_policy(self) -> None:
        raw = yaml.safe_load(CONTRACT_YAML.read_text(encoding="utf-8"))
        policy = load_presentation_policy(PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1)
        assert raw["slide_count"] == policy.slide_count

    def test_prompt_context_includes_policy_version_and_icons(self) -> None:
        policy = load_presentation_policy(PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1)
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
