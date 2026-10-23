Feature: A reply is saved even when the browser goes away
  As a signed-in user who refreshes or closes the tab while a reply is written
  I want the reply to be saved anyway
  So that it is there when I come back, and my question never dangles

  Scenario: The reply is saved after the client disconnects
    Given the Alter-Ego is writing a reply
    When the browser disconnects before it finishes
    Then the Alter-Ego still finishes the reply and saves it in its own database session

  Scenario: A reply that fails after the client disconnects is answered with an apology
    Given the browser disconnected while the reply was written
    When the reply then fails
    Then an apology turn is saved instead
