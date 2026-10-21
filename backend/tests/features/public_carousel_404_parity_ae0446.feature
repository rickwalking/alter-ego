# language: en
@AE-0446 @backend @public
Feature: Public carousel 404s do not reveal that a private carousel exists
  ADR-0013: a public route answers a private, unfinished and unknown carousel
  with the same 404, so the response cannot be used to probe which ids exist.

  Scenario: The viewer answers a private and an unknown carousel identically
    Given a private carousel exists
    When an anonymous visitor requests the public projection of the private carousel
    And an anonymous visitor requests the public projection of an unknown id
    Then both responses are a 404 with the same body

  Scenario: The viewer answers an unfinished public carousel like an unknown one
    Given a public carousel that is not completed exists
    When an anonymous visitor requests its public projection
    Then the response is the same 404 as for an unknown id

  Scenario: The public slide image route answers a private and an unknown carousel identically
    Given a private carousel with rendered slides exists
    When an anonymous visitor requests one of its public slide images
    And an anonymous visitor requests the same slide image for an unknown id
    Then both responses are a 404 with the same body

  Scenario: A private carousel that is not rendered yet answers like an unknown id
    Given a private carousel without rendered output exists
    When an anonymous visitor requests one of its public images
    Then the response is the same 404 as for an unknown id
