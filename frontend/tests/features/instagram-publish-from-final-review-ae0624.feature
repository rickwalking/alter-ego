Feature: The publish page offers Instagram "Publicar agora" at final review
  As the owner reviewing a carousel on the site
  I want the Instagram publish button while the carousel waits for my final review
  So that one click approves and posts it

  Scenario: A carousel at final review without an autopilot run is approved and published
    Given a carousel waiting for the owner's final review
    When the owner opens the publish page
    Then the Instagram publish button is shown and the site publish is not
    And after a successful publish the page refreshes the workflow state

  Scenario: A refused final-review approve publishes nothing
    Given the Instagram publish answers failed
    When the owner publishes from the final review
    Then the page shows the failure and does not refresh the workflow state

  Scenario: A carousel before final review is still refused
    Given a carousel before its final review, or a final review still running
    When the publish page decides which publishes to offer
    Then the Instagram publish button is not offered
