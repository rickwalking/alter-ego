# language: en
@AE-0452 @backend @public
Feature: The public carousel feed hides unfinished carousels and private fields
  The carousel list serves the public gallery to anonymous visitors. A public
  feed item carries what a card needs (titles, language, slides, images) and
  never the owner's drafts or internal state, and lists only finished carousels,
  the same rule the public viewer enforces.

  Scenario: An anonymous feed never lists an unfinished carousel
    Given a public carousel that is still generating
    When an anonymous visitor lists carousels without a status filter
    Then the generating carousel is not in the list
    And the total does not count it

  Scenario: An anonymous feed item carries no private fields
    Given a public completed carousel with a blog draft, an error message and an output directory
    When an anonymous visitor lists public carousels
    Then the item keeps its title and language
    And its blog markdown, caption, LinkedIn copy, error message, output directory and PDF paths are empty
    And it lists no research sources

  Scenario: A signed-in non-admin browsing the public feed gets the same redacted items
    Given a public completed carousel owned by another user with a blog draft
    When a signed-in editor lists carousels with public=true
    Then the item's blog markdown is empty

  Scenario: An admin listing carousels still sees the full project
    Given a public completed carousel with a blog draft
    When an admin lists carousels
    Then the item's blog markdown is returned
