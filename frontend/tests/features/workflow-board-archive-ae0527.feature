Feature: The owner archives and restores carousels on the workflow board
  As the site owner
  I want to archive a carousel I gave up on and restore it later
  So that the active board shows only work I still care about

  Scenario: Archiving a card asks for a confirmation first
    Given an active card that is neither published nor in progress
    When I choose "Arquivar"
    Then I am asked "Arquivar este carrossel?"
    And confirming archives the carousel and refreshes the board
    And cancelling archives nothing

  Scenario: A card in progress cannot be archived
    Given an active card whose phase run is live
    Then "Arquivar" is disabled and the reason is shown

  Scenario: A card an autopilot run still needs cannot be archived
    Given an active card with a scheduled autopilot publish
    Then "Arquivar" is disabled and the reason is shown

  Scenario: A phase stuck with a stale heartbeat can be archived
    Given an active card whose phase is in progress but its heartbeat is stale
    Then "Arquivar" is offered

  Scenario: A reviewer sees no archive control
    Given a card I review but do not own
    Then no "Arquivar" or "Restaurar" control is shown

  Scenario: A published card has no archive control
    Given a published card
    Then no "Arquivar" control is shown

  Scenario: The archived board lists archived carousels with restore
    When I choose "Arquivados"
    Then the board lists the archived carousels
    And each card offers "Restaurar", which restores it and refreshes the board

  Scenario: The archived board says when it is empty
    Given no archived carousels
    When I choose "Arquivados"
    Then I see "Nenhum carrossel arquivado."

  Scenario: A failed archive or restore says so on its card
    Given the server refuses the archive or the restore
    Then the card shows the failure and stays on the board
