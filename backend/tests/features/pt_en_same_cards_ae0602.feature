# AE-0602 — The EN translation keeps a quote card that the PT draft lost
Feature: PT and EN slides keep the same shape
  The EN translation is made once, from the drafts as they were then. The
  fail-closed retry can replace a slide's draft after that, and a re-drafted
  pov_news slide shows no quote card. EN must follow the PT slide: a card PT no
  longer has does not reach the content gate in EN alone.

  Scenario: The PT draft loses a quote card
    Given a POV slide whose EN translation has a quote card
    And the PT draft for that slide has no quote card
    When the content phase builds both locales
    Then both locales have the same cards
    And the content gate reports no translation_shape_mismatch for that slide

  Scenario: The fail-closed retry re-drafts a slide that showed a quote card
    Given a pov_news slide with its quote card in PT and EN
    And its draft cannot be parsed, so the slide blocks the first review
    And the single retry answers with a scaffold and no quote card
    When the content phase builds both locales
    Then neither locale shows the quote card
    And both locales are the same empty feature list
    And the content gate reports no translation_shape_mismatch

  Scenario: A card PT still has stays in both locales
    Given a slide with a quote card in PT and in its EN translation
    When the content phase builds both locales
    Then both locales show the quote card

  Scenario: The EN content kind follows PT when the card goes
    Given a PT draft of feature kind with no quote card
    And an EN translation of insight kind with a quote card
    When the content phase builds both locales
    Then the EN payload has the PT content kind and no quote card

  Scenario: The EN card goes when PT has no content kind either
    Given a PT draft with no quote card and no content kind
    And an EN translation of insight kind with a quote card
    When the content phase builds both locales
    Then the EN payload is recovered to the same empty feature list as PT

  Scenario: PT replaced the card with feature items
    Given a re-drafted PT slide with feature items and no quote card
    And an EN translation that still has the old quote card
    When the content phase builds both locales and the gate repair fills EN
    Then EN receives the PT feature items to translate
    And EN keeps no quote card
