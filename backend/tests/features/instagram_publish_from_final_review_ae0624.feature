Feature: Publish to Instagram from the site while the carousel is at final review
  As the owner reviewing a carousel on the site
  I want "Publicar agora" to work at final review, not only after a separate approval
  So that I can post the carousel from the publish page in one click

  Scenario: A carousel at final review without an autopilot run is approved and published
    Given a completed carousel at final review, awaiting the owner, with a saved caption
    When the owner publishes it to Instagram from the site
    Then its final review is approved first
    And the carousel is published with the saved caption

  Scenario: An autopilot carousel awaiting the owner is published like "Publicar agora"
    Given an autopilot run awaiting the owner's review of its carousel
    When the owner publishes the carousel from the site
    Then the run moves to publishing, the final review is approved and the carousel released
    And the run's own publish path posts it once

  Scenario: A scheduled autopilot carousel is published now
    Given an autopilot run scheduled for a later slot
    When the owner publishes the carousel from the site
    Then the run moves to publishing and the carousel is released

  Scenario: A refused final-review approve publishes nothing
    Given a carousel at final review whose approve is refused
    When the owner publishes it to Instagram from the site
    Then the route answers 409 "final_review_approve_refused"
    And nothing is posted and an autopilot run goes back to awaiting the owner

  Scenario: A failed release marks the run failed
    Given an autopilot run awaiting the owner whose carousel cannot be released
    When the owner publishes the carousel from the site
    Then the run is marked publish failed and nothing is posted

  Scenario: The approve runs only after every other check passed
    Given a carousel at final review whose caption on the page is not saved
    When the owner publishes it to Instagram from the site
    Then the route answers 409 "caption_not_saved"
    And the final review is not approved

  Scenario: A carousel before final review is still refused
    Given a carousel in the content phase
    When the owner publishes it to Instagram from the site
    Then the route answers 403 "workflow_not_approved_for_publish"

  Scenario: Runs that are not waiting for the owner are not published now
    Given an autopilot run that is generating, reworking or already published
    When the owner publishes the carousel from the site
    Then the approve is refused; a run already publishing is published through its own claim
