Feature: Public carousel title falls back to its topic
  As a visitor opening an older carousel that never got a generated title
  I want the page titled with the carousel's topic
  So that I never read "Untitled carousel" on a published carousel

  Scenario: An untitled carousel is titled with its topic
    Given a public carousel with topic "GPT 5.6 saiu" and no Portuguese or English title
    When I open it in Portuguese or English
    Then the heading, the page title and the share title read "GPT 5.6 saiu"

  Scenario: A localized title still wins over the topic
    Given a public carousel titled "Título PT" / "Title EN" with topic "Raw topic"
    When I open it in English
    Then the title reads "Title EN"

  Scenario: A carousel with neither title nor topic uses the localized fallback
    Given a public carousel with no title and no topic
    When I open it
    Then the title reads the localized "Untitled carousel"
