Feature: Change slide 1's photo on the publish step of a Ponto de Vista carousel (AE-0445)
  As the account owner
  I want a "Capa (slide 1)" picker on the publish page of a POV carousel
  So that I can swap slide 1's photo before I publish, without recreating the carousel

  Background:
    Given a completed carousel whose artifacts are ready on the publish page

  Scenario: The picker is shown for Ponto de Vista carousels only
    Given the carousel is in content mode "pov" or "pov_news"
    Then the publish page shows the "Capa (slide 1)" section
    Given the carousel is in content mode "news_analysis"
    Then the publish page does not show the "Capa (slide 1)" section

  Scenario: The options are thumbnails with the current photo marked
    Given the owner's library has the photos "A" and "B" and slide 1 shows "A"
    When the picker loads
    Then "A" and "B" are listed as thumbnails in a radio group
    And "A" is marked as the current cover
    And a GrokBot cover offer is labelled as such

  Scenario: The picker is keyboard accessible
    When the owner tabs to the photo "B" and presses Enter
    Then "B" is chosen

  Scenario: Choosing another photo switches the cover and refreshes the previews
    When the owner chooses "B"
    Then the page calls the cover endpoint with "B" and the workflow lock version
    And a progress message is shown while the slides re-render
    And on success the slide previews and PDF are refreshed with the new artifact version
    And a success message is shown

  Scenario: Choosing the current photo does nothing
    When the owner chooses "A"
    Then no request is sent

  Scenario: A version conflict shows a reload hint
    Given the cover endpoint answers 409
    When the owner chooses "B"
    Then an alert asks the owner to reload the page

  Scenario: Any other failure is visible
    Given the cover endpoint answers 422
    When the owner chooses "B"
    Then an alert says the cover could not be changed

  Scenario: An empty library explains where to add photos
    Given the owner's library is empty
    Then the picker says there are no photos and points to the create wizard

  Scenario: The options failing to load is visible
    Given the options endpoint fails
    Then an alert says the photos could not be loaded
