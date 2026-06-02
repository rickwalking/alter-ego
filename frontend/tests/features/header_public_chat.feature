Feature: Header Public Chat Link
  As a visitor
  I want chat available on the public shell but not on the blog header when anonymous
  So that public blog reading stays focused on content

  Background:
    Given the Header component is rendered

  # ---------------------------------------------------------------------------
  # Blog header (v1 layout)
  # ---------------------------------------------------------------------------

  Scenario: Anonymous user does not see Chat in blog header
    Given the user is not authenticated
    When the Header component renders
    Then the navigation does not contain "Chat"

  Scenario: Authenticated editor sees Chat in blog header
    Given the user has editor role
    When the Header component renders
    Then the navigation contains a "Chat" link
    And the link href is "/dashboard/chat"

  Scenario: Editor sees Knowledge Base and Create links
    Given the user has editor role
    When the Header component renders
    Then the navigation contains "Knowledge Base"
    And the navigation contains "Create"

  Scenario: Admin sees Admin link
    Given the user has admin role
    When the Header component renders
    Then the navigation contains "Admin"
    And the Admin link has red styling

  # ---------------------------------------------------------------------------
  # Non-Authenticated Link Visibility
  # ---------------------------------------------------------------------------

  Scenario: Knowledge Base is hidden from anonymous users
    Given the user is not authenticated
    When the Header component renders
    Then the navigation does not contain "Knowledge Base"

  Scenario: Create is hidden from anonymous users
    Given the user is not authenticated
    When the Header component renders
    Then the navigation does not contain "Create"

  Scenario: Admin is hidden from anonymous users
    Given the user is not authenticated
    When the Header component renders
    Then the navigation does not contain "Admin"

  # ---------------------------------------------------------------------------
  # Responsive Behavior
  # ---------------------------------------------------------------------------

  Scenario: Header is sticky on scroll
    Given the page is scrolled down
    Then the header remains visible at the top
    And the header has backdrop blur styling
