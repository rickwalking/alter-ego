Feature: Carousel i18n Blog and Design Token Endpoints

  Background:
    Given a carousel project exists with bilingual blog content

  Scenario: Get blog in Portuguese (default language)
    Given a carousel project with bilingual blog
    When GET /api/carousels/{id}/blog/pt
    Then returns 200 with Portuguese markdown
    And response language field is "pt"
    And available_languages includes "pt" and "en"

  Scenario: Get blog in English
    Given a carousel project with bilingual blog
    When GET /api/carousels/{id}/blog/en
    Then returns 200 with English markdown
    And response language field is "en"

  Scenario: Get blog in unavailable language
    Given a carousel project without English blog
    When GET /api/carousels/{id}/blog/en
    Then returns 404 with available languages in header

  Scenario: Get default blog (backward compatible)
    Given a carousel project with bilingual blog
    When GET /api/carousels/{id}/blog
    Then returns 200 with Portuguese markdown (default)

  Scenario: Get blog with design tokens
    Given a carousel project with generated design tokens
    When GET /api/carousels/{id}/blog/pt?include_design=true
    Then returns 200 with blog content and design tokens

  Scenario: Get design tokens separately
    Given a carousel project with generated design tokens
    When GET /api/carousels/{id}/design
    Then returns 200 with complete design tokens
    And tokens contain colors, typography, images, and layout

  Scenario: Get design tokens before generation
    Given a carousel project without design tokens
    When GET /api/carousels/{id}/design
    Then returns 404 with error message

  Scenario: Get carousel image file
    Given a carousel project with generated output files
    When GET /api/carousels/{id}/images/slide_1.jpg
    Then returns 200 with JPEG content type
    And response contains cache control headers

  Scenario: Get carousel image that does not exist
    Given a carousel project without output files
    When GET /api/carousels/{id}/images/nonexistent.jpg
    Then returns 404

  Scenario: Get slides for a carousel
    Given a carousel project with slides
    When GET /api/carousels/{id}/slides
    Then returns 200 with list of slides

  Scenario: Design tokens reflect chosen theme
    Given a carousel project with cybersecurity theme
    When design tokens are generated
    Then primary color is #ef4444
    And accent color is #00d4ff
    And background color is #0a0e17

  Scenario: Design tokens images reference carousel API URLs
    Given a carousel project
    When design tokens are generated
    Then hero image URL contains /api/carousels/{id}/images/hero
    And slide image URLs contain /api/carousels/{id}/images/slide_
