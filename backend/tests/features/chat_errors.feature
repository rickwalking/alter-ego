Feature: Chat errors are handled for the visitor, not shown to them
  As a visitor chatting with the Alter-Ego
  I want an honest answer or a plain "try again" when something goes wrong
  So that I never see a stack message and my next question is not mixed up with a failed one

  Scenario: A question the knowledge base cannot answer gets an honest reply
    Given the knowledge base has nothing about my question
    When the agent runs out of steps before answering
    Then I get a "not in my knowledge yet" reply instead of an error
    And the server logs that the step limit was reached

  Scenario: The honest reply is in the visitor's language
    When I ask in Portuguese
    Then the "not in my knowledge yet" reply is in Portuguese
    When I ask in English
    Then it is in English

  Scenario: The search tool stops after its budget
    Given the Alter-Ego may search 3 times per question
    When it asks for a 4th search
    Then the tool does not search and tells it to answer with what it has

  Scenario: A failed reply is logged on the server
    When the agent raises an error while answering
    Then the server logs the failure with the conversation id and the error type

  Scenario: The visitor sees a plain message, never the technical error
    When the agent raises an error while answering
    Then the error event says "Sorry, I couldn't answer that one. Please try again."
    And it contains no exception text or documentation link

  Scenario: A failed turn leaves no unanswered question behind
    When the agent raises an error while answering
    Then an apology assistant turn is saved after my message
    And no partial reply is saved

  Scenario: The visitor still gets the error event when the apology cannot be saved
    Given saving the apology turn fails
    When the agent raises an error while answering
    Then the server logs that the turn was not saved
    And the error event is still sent
