Feature: Calendar chips show clean, named titles
  As the site owner reading the content calendar
  I want every chip to show readable text and have an accessible name
  So that I never see raw HTML or a blank, unnamed chip

  Scenario: Emphasis markup in a title is not shown as raw HTML
    Given a calendar item titled "Por que todo mundo usa <strong>ChatGPT</strong> e não o Claude?"
    When the month grid shows it
    Then the chip reads "Por que todo mundo usa ChatGPT e não o Claude?"

  Scenario: An item without a title shows a localized placeholder
    Given a calendar item with an empty title
    When the month grid shows it
    Then the chip reads "Untitled" in English and "Sem título" in Portuguese

  Scenario: Every chip has an accessible name and a tooltip
    Given the month grid shows calendar items
    Then every chip button has a non-empty accessible name equal to its title
    And its full title is available as a tooltip
