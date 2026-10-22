"""Shared lower-third markup for the strategies that stack a block under the body.

Scenario: heading, body and the extra block render in order.
Scenario: artwork can be disabled through the render options.
Scenario: feature_item_html renders the icon, title and body.
"""

from __future__ import annotations

from rag_backend.application.services.carousel_template.strategies.hero_stack import (
    feature_item_html,
    render_hero_stack,
)
from rag_backend.domain.protocols.carousel import _RenderOptions

_SLIDE = {"number": 3, "heading": "**Bold** idea", "body": "Explained"}
_BLOCK = '<div class="extra">block</div>'


# Scenario: heading, body and the extra block render in order.
def test_heading_body_and_block_render_in_order() -> None:
    html = render_hero_stack(_SLIDE, _RenderOptions(total_slides=7), _BLOCK)

    assert (
        html.index("slide-hero-heading") < html.index("Explained") < html.index(_BLOCK)
    )
    assert "<strong>Bold</strong>" in html
    assert "3" in html


# Scenario: artwork can be disabled through the render options.
def test_artwork_can_be_disabled() -> None:
    with_art = render_hero_stack(_SLIDE, None, _BLOCK)
    without = render_hero_stack(_SLIDE, _RenderOptions(artwork=False), _BLOCK)

    assert "images/slide_3.jpg" in with_art
    assert "images/slide_3.jpg" not in without


# Scenario: feature_item_html renders the icon, title and body.
def test_feature_item_html_wraps_icon_title_and_body() -> None:
    html = feature_item_html('<span class="feature-icon">i</span>', "T **x**", "Body")

    assert html.startswith('<div class="feature-item"><span class="feature-icon">i')
    assert '<div class="feature-title">T <strong>x</strong></div>' in html
    assert '<div class="feature-body">Body</div>' in html
