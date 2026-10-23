@AE-0519 @frontend @dashboard
Feature: The palette archive confirmation is readable on any card width
  Scenario: The archive question sits on its own line above the buttons
    Given a custom palette card
    When the owner presses "Arquivar"
    Then "Arquivar esta paleta?" is shown as its own line above the "Cancelar" and "Arquivar" buttons
    And the question and both buttons form a group named by the question

  Scenario: Cancelling the archive question returns to the card actions
    Given the archive question is shown on a custom palette card
    When the owner presses "Cancelar"
    Then the question is gone and "Editar" and "Arquivar" are shown again
    And the palette is not archived
