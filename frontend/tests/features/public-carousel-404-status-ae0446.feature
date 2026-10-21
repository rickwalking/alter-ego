# language: en
@AE-0446 @frontend @public
Feature: The public carousel viewer answers a real 404 for an unknown carousel
  `/carousels/<id>` used to render the not-found UI with HTTP 200 because a
  route loading boundary streamed the page shell before `notFound()` ran.

  Scenario: An unknown carousel id answers a real 404
    Given no public carousel exists with the requested id
    When a visitor opens /carousels/<id>
    Then the HTTP status is 404
    And the not-found page is shown

  Scenario: The carousel gallery keeps its loading skeleton
    When a visitor opens /carousels while the feed loads
    Then the gallery loading skeleton is shown
