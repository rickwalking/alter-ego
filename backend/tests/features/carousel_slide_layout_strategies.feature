Feature: Carousel Slide Layout Strategies
  As a carousel author
  I want to choose and apply slide layout strategies
  So I can control how content, summary, and closing slides are visually rendered

  Background:
    Given a completed carousel project with 7 slides
    And persisted SlideData with features, stats, and insight

  Scenario: Select stat_card_grid strategy
    Given a carousel with 3 content slides
    When I select the "stat_card_grid" strategy
    Then content slides render stats as 3-column cards
    And the HTML contains ".stat-row" selector

  Scenario: Select feature_grid strategy
    Given a carousel with 3 content slides
    When I select the "feature_grid" strategy
    Then content slides render features as a 2-column grid
    And the HTML contains ".feature-grid.cols-2" selector

  Scenario: Select insight_quote strategy
    Given a carousel with a closing slide containing insight data
    When I select the "insight_quote" strategy
    Then the closing slide renders an accent-bordered quote card
    And the HTML contains ".insight-card" selector

  Scenario: Fallback for missing data
    Given a carousel with no stats data
    When I select the "stat_card_grid" strategy
    Then the strategy falls back to "hero_content" layout
    And the HTML does NOT contain ".stat-row"

  Scenario: Intro and CTA slides ignore strategy selection
    Given any selected strategy
    When rendering an intro or CTA slide
    Then the intro uses "intro_hero" layout regardless
    And the CTA uses "cta_centered" layout regardless

  Scenario: Strategy not found returns 422
    Given an invalid strategy name "nonexistent"
    When I PUT the strategy on the project
    Then the API returns 422 Unprocessable Entity

  Scenario: List available strategies
    When I GET /strategies
    Then the response contains a strategies array
    And each strategy has "name" and "display_name"

  Scenario: Active strategy persisted and readable
    Given I have applied the "feature_grid" strategy
    When I GET the carousel project
    Then the response includes slide_layout_strategy: "feature_grid"

  Scenario: Theme and strategy are orthogonal
    Given any selected strategy
    When I render a slide with a "cybersecurity" theme
    Then the strategy renders with cybersecurity colors
    And the theme values appear in the output

  Scenario: Bilingual rendering with strategy
    Given a bilingual carousel (pt + en)
    When I render with language "en"
    Then EN slides use the same strategy layout with translated text
