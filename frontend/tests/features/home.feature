Feature: Home Page

  As a visitor
  I want to see the landing page
  So that I understand what the application does

  Scenario: Display landing page with correct title
    Given I am on the home page
    Then I see the page title contains "Pedro Marins"
    And I see the main heading "Chat with my Alter-Ego to get to know me better"

  Scenario: Navigate to chat from CTA button
    Given I am on the home page
    When I click the "Start Chatting" button
    Then I am on the chat page

  Scenario: Feature cards are displayed
    Given I am on the home page
    Then I see the "Chat with My Alter-Ego" feature card
    And I see the "Blog Posts" feature card
    And I see the "Visual Carousels" feature card

  Scenario: Header navigation works
    Given I am on any page
    When I click the "Chat" link in the header
    Then I am on the chat page
    When I click the "Blog" link in the header
    Then I am on the blog page

  # ---------------------------------------------------------------------------
  # Locale-Aware Latest Posts
  # ---------------------------------------------------------------------------

  Scenario: Latest posts cards show English titles when locale is English
    Given the user's locale cookie is "en"
    And completed projects with title_en exist
    When I am on the home page
    Then the latest posts section displays cards with English titles

  Scenario: Latest posts cards show Portuguese titles when locale is Portuguese
    Given the user's locale cookie is "pt"
    And completed projects with Portuguese titles exist
    When I am on the home page
    Then the latest posts section displays cards with Portuguese titles

  Scenario: Latest posts cards use slide_1.jpg fallback when hero is missing
    Given a completed project has no hero image in design tokens
    When I am on the home page
    Then the card image src contains "/api/carousels/{id}/images/slide_1.jpg"

  Scenario: View all posts link navigates to blog
    Given I am on the home page
    When I click "View all posts"
    Then I am on the blog page
