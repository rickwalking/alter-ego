Feature: The workflow board keeps its place while it refreshes (AE-0450)
  As a signed-in owner reading the workflow board
  I want the background refresh to update the cards in place
  So that the page does not jump back to the top every poll

  # Tests:
  #   src/app/dashboard/workflow/page.test.tsx

  Background:
    Given the workflow board has loaded its cards

  Scenario: A poll refresh keeps the mounted board
    When the board polls the API and the new data arrives
    Then no loading spinner replaces the board while the request runs
    And the board columns are the same DOM nodes as before
    And the updated cards are shown

  Scenario: A focus refresh keeps the mounted board
    When the window regains focus and the board refetches
    Then no loading spinner replaces the board while the request runs
    And the board columns are the same DOM nodes as before

  Scenario: A failed refresh keeps the last board on screen
    When a background refresh fails
    Then the error message and the retry button are shown
    And the last loaded board stays mounted

  Scenario: The first load shows the spinner until the board arrives
    Given no board has loaded yet
    When the first request is still running
    Then the loading spinner is shown and no board is rendered
