Feature: Carousel publish workspace
  As a carousel author
  I want to preview, edit, and publish my carousel
  So I can ship to Instagram and LinkedIn without leaving the app

  Background:
    Given a completed carousel with IG caption and PT + EN LinkedIn posts
    And four slide images available at design_tokens.images.slides

  # Carousel preview --------------------------------------------------

  Scenario: The carousel renders all slides with dot indicators
    When the user opens /create/{id}/publish
    Then the viewer shows 4 slides in horizontal order
    And 4 dot indicators appear under the viewport

  # Instagram tab -----------------------------------------------------

  Scenario: Instagram caption editor shows live char counter
    When the user types into the Instagram caption
    Then the character counter updates on every keystroke
    And the counter turns red once it exceeds 2200

  Scenario: Hashtag counter flags over-limit state
    Given the user pastes a caption with 31 hashtags
    Then a red warning explains Instagram rejects over 30 hashtags
    And the "Publish to Instagram" button is disabled

  Scenario: Copy caption writes to clipboard
    When the user clicks "Copy caption"
    Then navigator.clipboard.writeText is called with the current caption

  # LinkedIn tab -----------------------------------------------------

  Scenario: LinkedIn post language toggle swaps content
    Given the user switches to the LinkedIn tab
    And linkedin_post_pt contains Portuguese text
    And linkedin_post_en contains English text
    When the user clicks the "EN" language button
    Then the editor body is the English post

  Scenario: Download PDF link points to the pdf route
    When the user clicks "Download PDF"
    Then the browser navigates to /api/carousels/{id}/pdf

  Scenario: Open LinkedIn points to the compose URL
    When the user clicks "Open LinkedIn"
    Then the browser navigates to https://www.linkedin.com/feed/?shareActive=true
    And manual-step instructions remain visible on the page
