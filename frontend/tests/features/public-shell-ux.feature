Feature: Public shell UX

  Scenario: Homepage does not show dashboard sidebar
    When I open "/"
    Then the neon dashboard sidebar is not visible

  Scenario: Public chat does not list conversation history
    When I open "/chat"
    Then the conversation history sidebar is not visible

  Scenario: Language switch sets locale on homepage
    When I switch language to "pt" on the public header
    Then the locale cookie is "pt"

  Scenario: Blog post from homepage uses neon public blog
    When I open "/"
    And I follow the first latest post link
    Then the page does not use the legacy blog Header layout
