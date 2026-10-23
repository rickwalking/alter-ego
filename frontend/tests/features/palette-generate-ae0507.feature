@AE-0507 @frontend @dashboard
Feature: Create a palette with AI in the New palette modal
  Scenario: Generating shows three candidates to pick from
    Given the New palette modal is open
    When the owner types "Descreva a paleta" text and presses "Gerar"
    Then three candidate cards with a swatch, a name and the contrast are shown

  Scenario: Fewer than three candidates say how many are shown
    Given the generator returns fewer than three candidates
    When the owner presses "Gerar"
    Then the cards are shown with a "Mostrando N de 3" note

  Scenario: Using a candidate pre-fills the form without saving
    Given the generator shows candidates
    When the owner presses "Usar" on one candidate
    Then the name, colours, mode and keywords of the form take its values
    And no palette is created until "Criar paleta" is pressed

  Scenario: A generator failure shows a retryable error
    Given the generator request fails
    When the owner presses "Gerar"
    Then a retryable error is shown
    And the manual form still creates a palette

  Scenario: The generator needs a description
    Given the New palette modal is open with an empty description
    Then "Gerar" is disabled

  Scenario: The edit modal has no generator
    Given the edit modal of a custom palette
    Then the "Descreva a paleta" field is not shown
