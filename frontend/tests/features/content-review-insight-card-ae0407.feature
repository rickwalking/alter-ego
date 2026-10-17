Feature: pov_news quote card in the dashboard content review (AE-0407)
  As a carousel owner reviewing a pov_news deck
  I want a slide's quote card shown as a quote with its author and handle
  So that I review what the slide will show instead of raw JSON

  # Backend shape: backend/src/rag_backend/domain/news_quote_cards.py (quote_card)
  # Tests:
  #   src/modules/editorial/workspace/lib/presentation-insight-quote.test.ts
  #   src/modules/editorial/workspace/components/presentation-insight-quote-card.test.tsx
  #   src/app/dashboard/create/workspace/phase-review/content-phase-locale-fields.test.tsx

  Background:
    Given a content-review slide whose locale payload has an "insight" quote card
    And the card is {"quote": "Ship small", "name": "Taylor H", "handle": "taylorhbuilds"}

  Scenario: The quote card renders in both locale columns
    When the owner opens the content review
    Then the PT and the EN column each show the label "Quote card"
    And each shows the quote "Ship small" as a blockquote
    And each shows "Taylor H" and "@taylorhbuilds · X"
    And neither shows the label "Structured field: insight" nor raw JSON

  Scenario: A handle that already starts with @ is not doubled
    Given the card handle is "@taylorhbuilds"
    When the owner opens the content review
    Then the card shows "@taylorhbuilds · X"
    And it does not show "@@taylorhbuilds"

  Scenario: A url in the payload is never shown
    Given the card also has "url": "https://x.com/taylorhbuilds/status/1"
    When the owner opens the content review
    Then the card does not show the url

  Scenario: The name falls back to the attribution
    Given the card has no "name" but has "attribution": "Taylor H"
    When the owner opens the content review
    Then the card shows "Taylor H"

  Scenario: The quote card is an accessible figure
    When the owner opens the content review
    Then the card is a figure named "Quote from Taylor H"
    And the author line is its figcaption

  Scenario: A malformed insight keeps the JSON fallback
    Given the insight has no "quote" or no "handle"
    When the owner opens the content review
    Then the slide shows the label "Structured field: insight"
    And the insight is shown as a JSON block
    And no quote card is rendered
