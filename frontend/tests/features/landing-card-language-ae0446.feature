# language: en
@AE-0446 @frontend @public
Feature: A post card shows its title and subtitle in one language
  The landing "Latest Posts" cards and the public blog cards built from carousel
  projects never mix an English title with a Portuguese subtitle (or the reverse).

  Scenario: An English visitor sees the English title and English subtitle
    Given a carousel with Portuguese and English titles and subtitles
    When an English visitor sees its card
    Then the title and the subtitle are both English

  Scenario: An English title without an English subtitle shows no Portuguese subtitle
    Given a carousel with an English title but only a Portuguese subtitle
    When an English visitor sees its card
    Then the title is English
    And no Portuguese subtitle is shown under it

  Scenario: A Portuguese visitor sees the Portuguese copy
    Given a carousel with Portuguese and English titles and subtitles
    When a Portuguese visitor sees its card
    Then the title and the subtitle are both Portuguese

  Scenario: A card without a Portuguese title falls back to English as a whole
    Given a carousel with only an English title and English subtitle
    When a Portuguese visitor sees its card
    Then the title and the subtitle are both English

  Scenario: A card without an English title stays Portuguese for an English visitor
    Given a carousel with only Portuguese copy
    When an English visitor sees its card
    Then the title and the subtitle are both Portuguese

  Scenario: A landing card opens the carousel it shows
    Given the landing "Latest Posts" lists a published carousel
    When a visitor follows its card
    Then the link opens the public carousel viewer for that carousel
    And no request is made for a blog post with the carousel id
