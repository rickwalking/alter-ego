Feature: Checklist slide items are edited exactly as they are shown
  As the owner editing a carousel
  I want the editor to show and change the very text each slide displays
  So that my edits to a checklist appear on the slide

  Scenario: The editor knows which slides render items as checklist lines
    Given a "Ponto de Vista" deck whose save slide renders a checklist
    Then the workflow state marks that slide as a checklist slide
    And a deck whose chosen layout is the checklist marks its summary and closing slides
    And other decks mark none

  Scenario: An edited checklist item renders on the slide
    Given a checklist item whose displayed line was edited
    Then the slide HTML shows the edited text, in Portuguese and in English

  Scenario: A repair moves hidden checklist text into the displayed line
    Given a checklist item whose body differs from its displayed title
    When the repair runs with --apply
    Then the body becomes the displayed text, the body is cleared, and the carousel is republished
    And a dry run changes nothing, and a second run finds nothing to change
