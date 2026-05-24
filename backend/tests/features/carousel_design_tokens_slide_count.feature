Feature: Carousel design tokens reflect actual slide count
  As a carousel publisher
  I want design_tokens to contain the correct number of slides based on slides_config
  So that the publish panel shows all rendered slides

  Background:
    Given a carousel project exists

  Scenario: Design tokens use slide_count_from_config for N_slides format
    Given the project has slides_config "7_slides"
    When generate_design_tokens is called
    Then the design tokens contain 7 slides
    And progress_segments is 7

  Scenario: Design tokens use slide_count_from_config for comma format
    Given the project has slides_config "1 intro, 3 content, 1 closing, 1 cta"
    When generate_design_tokens is called
    Then the design tokens contain 6 slides
    And progress_segments is 6

  Scenario: Design tokens fall back to MAX_SLIDES for unparseable config
    Given the project has slides_config "invalid_format"
    When generate_design_tokens is called
    Then the design tokens contain 7 slides
    And progress_segments is 7

  Scenario: Design tokens use slide_count_from_config for "6_slides"
    Given the project has slides_config "6_slides"
    When generate_design_tokens is called
    Then the design tokens contain 6 slides
    And progress_segments is 6

  Scenario: Backfill endpoint regenerates tokens for all completed carousels
    Given 3 completed carousels exist with stale design_tokens
    When POST /api/admin/carousels/refresh-design-tokens is called
    Then all 3 carousels have updated design_tokens with correct slide counts
