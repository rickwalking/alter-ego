"""Shared fixtures for carousel template tests."""

import pytest

from rag_backend.domain.models import CarouselProject, CarouselTheme


@pytest.fixture
def sample_project():
    """Create a sample carousel project for testing."""
    project = CarouselProject(
        topic="Machine Learning Basics",
        audience="Beginners",
        niche="AI Education",
        theme=CarouselTheme.AI_COMPETITION,
    )
    project.set_title(title="Master ML in 7 Slides", subtitle="A beginner's guide")
    return project


@pytest.fixture
def sample_theme():
    """Create a sample theme dict for testing."""
    return {
        "primary": "#3b82f6",
        "accent": "#f59e0b",
        "background": "#0a0e17",
    }


@pytest.fixture
def sample_research_context():
    """Create sample research context text."""
    return "Source: https://example.com/ml\nMachine learning is a subset of artificial intelligence..."
