# language: en
@AE-0444 @frontend @public
Feature: Public carousel gallery
  A visitor can browse every published carousel, newest first, with a clear
  cover, title, date, language, and slide count.

  Scenario: Anonymous visitors are not redirected to login
    Given a visitor without a session
    When they open /carousels
    Then the gallery renders instead of redirecting to /login

  Scenario: The gallery lists public completed carousels
    Given the public feed has published carousels
    When a visitor opens /carousels
    Then each card links to its viewer
    And each card shows the cover, title, date, language, and slide count

  Scenario: The gallery is paginated
    Given the public feed has more carousels than one page
    When a visitor opens /carousels
    Then only the first page of cards is shown
    And a next-page link is available

  Scenario: An empty gallery has an empty state
    Given the public feed has no published carousels
    When a visitor opens /carousels
    Then a friendly empty state is shown
    And no card grid is rendered

  Scenario: A failed feed request does not crash the page
    Given the public feed request fails
    When a visitor opens /carousels
    Then the page renders the empty state instead of throwing
