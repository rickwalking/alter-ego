# Ticket: AE-0443 — landing copy, card links, header and hero badge
# Owner request 2026-10-20. Copy is reviewed in both locales; counts are derived
# from data, never guessed.

Feature: Landing page truth, links and public header
  As a visitor
  I want the landing page to make only true claims and lead me to each section
  So that I can trust the page and reach the content I came for

  Background:
    Given I am on the landing page

  # ---------------------------------------------------------------------------
  # Stats derived from data
  # ---------------------------------------------------------------------------

  Scenario: Published-carousel stat comes from the public carousel total
    Given the public carousel list reports a total of 15
    When the stats section renders
    Then the carousel stat shows "15"
    And the stats section does not show a hardcoded "50+"

  Scenario: The stats block only shows true and meaningful claims
    Given the public carousel list reports a total of 15
    When the stats section renders
    Then the stats section shows the years-of-engineering claim
    And the stats section does not show an "∞" topics claim

  # ---------------------------------------------------------------------------
  # Capability cards link to their sections
  # ---------------------------------------------------------------------------

  Scenario: Every capability card links to its public route
    When the capabilities section renders
    Then the "Blog Posts" card links to "/blog"
    And the "Visual Carousels" card links to "/carousels"
    And the "Chat with My Alter-Ego" card links to "/chat"

  Scenario: A capability card is one whole-card link
    When I click anywhere on the "Visual Carousels" card
    Then I navigate to "/carousels"

  Scenario: Capability cards are keyboard accessible
    When I focus the "Blog Posts" card with the keyboard
    Then the card shows a visible focus ring

  # ---------------------------------------------------------------------------
  # Public header
  # ---------------------------------------------------------------------------

  Scenario: The public header does not offer Login
    When the public header renders
    Then the header navigation does not contain a "Login" link
    But the login page is still reachable by its direct URL

  Scenario: The public header links to Carousels next to Blog
    When the public header renders
    Then the header navigation contains a "Carousels" link after "Blog"
    And the Carousels link href is "/carousels"

  # ---------------------------------------------------------------------------
  # Hero
  # ---------------------------------------------------------------------------

  Scenario: The hero no longer shows the version badge
    When the hero renders
    Then the hero does not show "Alter-Ego v2.0"
    And the hero still shows the main heading and CTAs

  # ---------------------------------------------------------------------------
  # Copy review, pt/en in sync
  # ---------------------------------------------------------------------------

  Scenario: Landing copy is complete and in sync in both locales
    Then every landing translation key exists in both pt and en
    And neither locale contains the removed hero version badge key
    And neither locale contains the removed topics stat key

  Scenario: Landing copy makes no overclaim or grammar error
    Then the hero subtitle does not claim the assistant knows everything
    And the Portuguese About bio has no "Especializo me" grammar error
    And the latest-posts subtitle describes carousels, not blog posts
