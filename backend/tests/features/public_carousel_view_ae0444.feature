# language: en
@AE-0444 @backend @public
Feature: Public carousel viewer projection
  Anonymous visitors can read a lean, public projection of a published carousel
  without exposing owner-only preview URLs or internal file paths.

  Background:
    Given a carousel project exists

  Scenario: A public completed carousel is readable
    Given the carousel is public and completed
    And it has Portuguese and English rendered slides
    When an anonymous visitor requests the public projection
    Then the response lists the carousel title and creation date
    And slides are grouped under "pt" and "en"
    And every slide carries its number, heading, and public image URL
    And the cover uses the first public slide image

  Scenario: A private carousel is not readable
    Given the carousel is not public
    When an anonymous visitor requests the public projection
    Then the response is a 404

  Scenario: A non-completed carousel is not readable
    Given the carousel is public but not completed
    When an anonymous visitor requests the public projection
    Then the response is a 404

  Scenario: An unknown carousel is not readable
    When an anonymous visitor requests the public projection for an unknown id
    Then the response is a 404

  Scenario: Preview image URLs never leak
    Given the carousel is public and completed
    And its stored tokens contain owner preview image URLs
    When an anonymous visitor requests the public projection
    Then no returned URL contains "/preview/"

  Scenario: A carousel with only Portuguese slides reports one language
    Given the carousel is public and completed
    And it has only Portuguese rendered slides
    When an anonymous visitor requests the public projection
    Then "available_languages" contains only "pt"

  Scenario: The public feed is newest-first by creation date
    Given several public completed carousels exist
    When an anonymous visitor lists them with sort=created_at
    Then the newest created carousel comes first

  Scenario: The public feed exposes the content language
    Given a public completed carousel exists
    When an anonymous visitor lists public completed carousels
    Then each item reports its stored language
