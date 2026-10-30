Feature: The workflow board is keyboard and screen reader accessible
  As the site owner
  I want to move across board cards with the keyboard and reach archive
  actions from a per-card menu
  So that the board costs a couple of tab stops instead of dozens

  Scenario: The card grid costs one tab stop and arrows move between cards
    Given a board with cards in several columns
    When I press Tab into the board
    Then exactly one card link is in the tab order
    And Arrow Down and Arrow Up move within the column without leaving it
    And Arrow Right and Arrow Left jump to the same position in the adjacent non-empty column
    And Home and End go to the first and last card of the column
    And Enter opens the focused card

  Scenario: A column announces itself and its count
    Given a column with three cards
    Then the column is a labelled region
    And its card list announces three items

  Scenario: The new-carousel action is one link styled as a button
    Given the workflow board top bar
    Then "Novo carrossel" is a link, not a button nested in a link

  Scenario: A segmented control switches between active and archived
    Given the workflow board top bar
    Then "Ativos" and "Arquivados" form a radiogroup with arrow-key navigation
    When I choose "Arquivados"
    Then the URL carries archived=1 and the top bar title reads "Arquivados"
    When I choose "Ativos"
    Then the URL drops archived and the title reads "Quadro de Workflow"

  Scenario: The archive action lives behind a per-card overflow menu
    Given a card I may archive
    Then a "Mais ações" overflow button sits outside the card link
    When I open it and choose "Arquivar"
    Then I am asked "Arquivar este carrossel?" and confirming archives the card
    And Escape closes the menu and returns focus to the overflow button

  Scenario: A refused card explains itself once, inside its menu
    Given a card whose phase run is live
    Then the card shows no repeated refusal sentence
    When I open its "Mais ações" menu
    Then the menu shows the refusal reason as disabled text

  Scenario: A card without archive rights shows no control
    Given a card I review but do not own
    Then no overflow button is shown
    Given a published card
    Then no overflow button is shown

  Scenario: The archived board restores through the same menu
    Given the archived board
    When I open a card's menu and choose "Restaurar"
    Then the carousel is restored and the board refreshes
