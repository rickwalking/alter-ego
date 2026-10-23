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

  Scenario: Tokens reach the client while the reply is written
    When the Alter-Ego writes the first words of a reply
    Then they reach the browser before the reply is finished

  Scenario: One reply at a time per conversation
    Given a reply to my conversation is still being written
    When another message for that conversation arrives
    Then it is refused (409 before the stream, or an error event) and nothing else is started

  Scenario: Shutdown answers the replies still being written
    Given a reply is still being written when the server shuts down
    When it does not finish within the drain timeout
    Then it is cancelled and an apology turn is saved
