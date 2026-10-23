Feature: The Knowledge Base lists the content sources of my carousels
  As the site owner
  I want to see the sources I attached to my carousels in one place
  So that I can find which carousel used which source

  Scenario: My carousels' sources are listed newest first with their carousel
    Given my carousel "IA no trabalho" with a URL source and a note source
    When I list my carousel sources
    Then both sources are listed, newest first
    And each one names the carousel "IA no trabalho" and its id
    And the URL source carries its URL and the note source carries none

  Scenario: The list paginates
    Given my carousel with 3 sources
    When I list my carousel sources 2 at a time from offset 2
    Then 1 source is listed and the total is 3

  Scenario: The list can be filtered by carousel
    Given my two carousels with sources
    When I list the sources of one of them
    Then only that carousel's sources are listed
    And the carousel facets still name both carousels with their source counts

  Scenario: Another owner's sources are never listed
    Given a carousel of another editor with a source
    When I list my carousel sources
    Then nothing is listed and the total is 0

  Scenario: An admin sees every owner's sources
    Given a carousel of another editor with a source
    When an admin lists the carousel sources
    Then that source is listed

  Scenario: Sources of a blog post are not carousel sources
    Given a source attached to a blog post only
    When I list my carousel sources
    Then nothing is listed

  Scenario: An anonymous visitor cannot list carousel sources
    When a visitor who is not signed in lists the carousel sources
    Then the request is refused with 401

  Scenario: A page size over 100 is refused
    When I list my carousel sources 101 at a time
    Then the request is refused with 422
