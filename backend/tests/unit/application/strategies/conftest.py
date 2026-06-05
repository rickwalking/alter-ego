"""Shared fixtures for slide layout strategy tests."""

import pytest

from rag_backend.application.services.carousel_template.strategies import (
    CtaCenteredStrategy,
    FeatureGridStrategy,
    HeroContentStrategy,
    InsightQuoteStrategy,
    IntroHeroStrategy,
    NumberedListStrategy,
    StatCardGridStrategy,
)
from rag_backend.application.services.carousel_template.strategies.registry import (
    bootstrap_strategies,
)
from rag_backend.domain.models import CarouselProject, CarouselTheme


@pytest.fixture
def sample_project():
    project = CarouselProject(
        topic="Machine Learning Basics",
        audience="Beginners",
        niche="AI Education",
        theme=CarouselTheme.AI_COMPETITION,
    )
    project.set_title(title="Master ML in 7 Slides", subtitle="A beginner's guide")
    project.creator_name = "AI Academy"
    project.creator_handle = "ai_academy"
    return project


@pytest.fixture
def sample_theme():
    return {
        "primary": "#3b82f6",
        "accent": "#f59e0b",
        "background": "#0a0e17",
    }


@pytest.fixture
def registry():
    return bootstrap_strategies()


@pytest.fixture
def all_strategies():
    return [
        IntroHeroStrategy(),
        HeroContentStrategy(),
        CtaCenteredStrategy(),
        StatCardGridStrategy(),
        FeatureGridStrategy(),
        InsightQuoteStrategy(),
        NumberedListStrategy(),
    ]


@pytest.fixture
def slide_with_stats():
    return {
        "number": "3",
        "type": "content",
        "heading": "Key Metrics",
        "body": "Our growth in numbers",
        "stats": [
            {"value": "10K+", "label": "Users", "detail": "Active monthly"},
            {"value": "99.9%", "label": "Uptime", "detail": "SLA achieved"},
            {"value": "50+", "label": "Countries", "detail": "Worldwide reach"},
        ],
        "features": [],
        "insight": None,
        "summary_points": [],
        "tldr_strip": None,
    }


@pytest.fixture
def slide_with_features():
    return {
        "number": "4",
        "type": "content",
        "heading": "Core Features",
        "body": "What makes us different",
        "stats": [],
        "features": [
            {"icon": "⚡", "title": "Fast", "body": "Lightning speed processing"},
            {"icon": "🔒", "title": "Secure", "body": "End-to-end encryption"},
            {"icon": "☁️", "title": "Cloud", "body": "Auto-scaling infrastructure"},
        ],
        "insight": None,
        "summary_points": [],
        "tldr_strip": None,
    }


@pytest.fixture
def slide_with_insight():
    return {
        "number": "5",
        "type": "closing",
        "heading": "Key Insight",
        "body": "",
        "stats": [],
        "features": [],
        "insight": {
            "quote": "AI will transform every industry",
            "attribution": "Andrew Ng",
        },
        "summary_points": [],
        "tldr_strip": None,
    }


@pytest.fixture
def slide_empty():
    return {
        "number": "6",
        "type": "content",
        "heading": "Empty Slide",
        "body": "No structured data here",
        "stats": None,
        "features": None,
        "insight": None,
        "summary_points": [],
        "tldr_strip": None,
    }


@pytest.fixture
def slide_with_overflow():
    return {
        "number": "3",
        "type": "content",
        "heading": "Overflow Test",
        "body": "Testing max items cap",
        "stats": [
            {"value": f"Val{i}", "label": f"Label{i}", "detail": f"Detail{i}"}
            for i in range(10)
        ],
        "features": [
            {"icon": "🔹", "title": f"Feature {i}", "body": f"Body {i}"}
            for i in range(10)
        ],
        "insight": None,
        "summary_points": [],
        "tldr_strip": None,
    }
