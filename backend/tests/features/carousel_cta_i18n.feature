Feature: Carousel CTA Slide i18n
  As an international visitor
  I want the CTA slide to be in my language
  So that I can understand the call-to-action

  Background:
    Given a completed carousel project exists

  Scenario: Last slide CTA buttons are in English
    Given I view the carousel in English
    When I reach the last slide
    Then the primary CTA button should say "Save this post"
    And the secondary CTA button should say "Share"

  Scenario: Last slide CTA buttons are in Portuguese
    Given I view the carousel in Portuguese
    When I reach the last slide
    Then the primary CTA button should say "Salve este post"
    And the secondary CTA button should say "Compartilhe"

  Scenario: CTA slide text is in English for English carousel
    Given I view the carousel in English
    When I reach the last slide
    Then the CTA heading and body should be in English

  Scenario: CTA slide text is in Portuguese for Portuguese carousel
    Given I view the carousel in Portuguese
    When I reach the last slide
    Then the CTA heading and body should be in Portuguese
