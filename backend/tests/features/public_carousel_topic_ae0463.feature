Feature: Public carousel viewer carries the topic
  As a visitor opening an older carousel that never got a generated title
  I want the viewer to know the carousel's topic
  So that the page can be titled with it instead of "Untitled carousel"

  Scenario: The public viewer payload carries the topic
    Given a public completed carousel with topic "GPT 5.6 saiu" and no title
    When the anonymous viewer projection is read
    Then it carries topic "GPT 5.6 saiu" and a null title
