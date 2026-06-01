Feature: Carousel publish workspace
  As a carousel author
  I want to preview, edit, and publish my carousel
  So I can ship to Instagram and LinkedIn without leaving the app

  Background:
    Given a completed carousel with IG caption and PT + EN LinkedIn posts
    And four slide images available at design_tokens.images.slides

  # Carousel preview --------------------------------------------------

  Scenario: The carousel renders all slides with dot indicators
    When the user opens /dashboard/create/{id}/publish
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

  # Chat persistence --------------------------------------------------

  Scenario: Chat history survives page refresh
    Given a publish page with an existing conversation containing 3 messages
    When the user refreshes the page
    Then all 3 messages are still visible
    And the message input is ready for a new message

  Scenario: Invalid conversation ID is replaced on refresh
    Given the browser has a stale conversation ID in localStorage
    When the user opens the publish page
    Then a new conversation is created
    And the stale ID is removed from localStorage

  Scenario: Mismatched conversation ID is replaced on refresh
    Given the browser has a conversation ID for another carousel in localStorage
    When the user opens the publish page
    Then the mismatched ID is removed from localStorage
    And a new project-scoped conversation is created

  Scenario: Publish chat uses a project-scoped WebSocket
    Given a valid conversation exists for the carousel
    When the publish chat connects
    Then the WebSocket URL contains the conversation ID
    And HTTPS pages use the secure WebSocket protocol

  Scenario: Rapid page refreshes do not create duplicate conversations
    Given no conversation exists for the project
    When the publish page mounts twice in rapid succession
    Then only one conversation creation request is sent

  Scenario: Agent context is preserved across refreshes
    Given a conversation where the user asked to "shorten the caption"
    And the agent responded with a shorter caption
    When the user refreshes the page
    Then the previous messages are loaded
    And a subsequent message sent via WebSocket includes the full history
