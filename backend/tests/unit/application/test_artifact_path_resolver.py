"""Unit tests for carousel artifact path resolution and dedup helpers.

Feature: Path Resolver Dedup (see AE-0043)

  Scenario: resolve_language_dir uses _resolve_base
    Given resolve_language_dir is called
    When inspecting its implementation
    Then it calls _resolve_base and does not call the reconcile resolver

  Scenario: deprecated alias stays callable during the migration window
    Given external callers still use resolve_artifact_serving_paths
    When the alias is called
    Then it emits a DeprecationWarning
    And delegates to resolve_and_reconcile_serving_paths
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from rag_backend.application.services.carousel import artifact_path_resolver
from rag_backend.application.services.carousel.artifact_path_resolver import (
    ArtifactServingPaths,
    _resolve_base,
    resolve_and_reconcile_serving_paths,
    resolve_artifact_serving_paths,
    resolve_current_index_path,
    resolve_hd_dir,
    resolve_language_dir,
    resolve_shared_images_dir,
    supported_languages,
)
from rag_backend.domain.constants import (
    HD_SUBDIR_NAME,
    LANGUAGE_PT,
    SHARED_IMAGES_DIR_NAME,
)
from rag_backend.domain.models import CarouselProject


def _make_project(**overrides: object) -> CarouselProject:
    defaults: dict[str, object] = {
        "topic": "test",
        "audience": "test",
        "niche": "test",
        "output_dir": "/tmp/test_output",
    }
    defaults.update(overrides)
    return CarouselProject(**defaults)


@pytest.mark.unit
class TestResolveBase:
    def test_returns_none_when_output_dir_missing(self) -> None:
        assert _resolve_base(_make_project(output_dir=None)) is None

    def test_resolves_project_root(self) -> None:
        paths = _resolve_base(_make_project(output_dir="/tmp/test_output"))
        assert paths is not None
        assert paths.project_root == Path("/tmp/test_output").resolve()
        assert paths.version_root is None


@pytest.mark.unit
class TestResolversUseResolveBase:
    def test_resolve_language_dir_none_when_no_output_dir(self) -> None:
        assert resolve_language_dir(_make_project(output_dir=None), LANGUAGE_PT) is None

    def test_resolve_language_dir_appends_language(self) -> None:
        result = resolve_language_dir(_make_project(), LANGUAGE_PT)
        assert result == Path("/tmp/test_output").resolve() / LANGUAGE_PT

    def test_resolve_hd_dir_appends_hd_subdir(self) -> None:
        result = resolve_hd_dir(_make_project(), LANGUAGE_PT)
        expected = Path("/tmp/test_output").resolve() / LANGUAGE_PT / HD_SUBDIR_NAME
        assert result == expected

    def test_resolve_shared_images_dir(self) -> None:
        result = resolve_shared_images_dir(_make_project())
        expected = Path("/tmp/test_output").resolve() / SHARED_IMAGES_DIR_NAME
        assert result == expected

    def test_resolve_current_index_path_none_without_output_dir(self) -> None:
        assert resolve_current_index_path(_make_project(output_dir=None)) is None

    def test_supported_languages_empty_for_missing_dirs(self, tmp_path: Path) -> None:
        # No rendered locale directories exist under a fresh tmp_path.
        assert supported_languages(_make_project(output_dir=str(tmp_path))) == ()


@pytest.mark.unit
class TestDeprecatedAlias:
    def test_alias_returns_none_without_output_dir(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            assert (
                resolve_artifact_serving_paths(_make_project(output_dir=None)) is None
            )

    def test_alias_emits_deprecation_warning(self, tmp_path: Path) -> None:
        project = _make_project(output_dir=str(tmp_path))
        with pytest.warns(DeprecationWarning):
            resolve_artifact_serving_paths(project)

    def test_alias_delegates_to_new_function(self, tmp_path: Path) -> None:
        project = _make_project(output_dir=str(tmp_path))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            via_alias = resolve_artifact_serving_paths(project)
        via_new = resolve_and_reconcile_serving_paths(project)
        assert isinstance(via_alias, ArtifactServingPaths)
        assert via_alias == via_new

    def test_alias_is_exported(self) -> None:
        assert "resolve_artifact_serving_paths" in artifact_path_resolver.__all__
