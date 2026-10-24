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

  Scenario: The start response carries the checklist slides
    Given a "Ponto de Vista" deck whose start run returns its localized slides
    When the workflow is started and its state is read
    Then both responses list the save slide as a checklist slide
    And a start response never wipes the checklist slides the editor holds
