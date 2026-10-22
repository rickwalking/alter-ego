Feature: Mobile pages never scroll sideways
  As a visitor or the owner on a phone (375 and 390 px wide)
  I want the page to fit the screen width
  So that nothing is clipped and the page never pans horizontally

  Scenario: The homepage fits a 375 px screen
    Given I open the homepage on a 375 px wide phone
    When I scroll through every section
    Then the page is never wider than the screen

  Scenario: The social links wrap instead of overflowing
    Given the About section's LinkedIn, GitHub and Instagram links
    When the row is narrower than the three links
    Then the links wrap onto a new line

  Scenario: The calendar top bar fits a 375 px screen
    Given I open the content calendar on a 375 px wide phone
    Then the "Schedule Post" button is fully on screen and the breadcrumb is hidden
