Feature: Boost requests are stored on Postgres
  The bot's boost request writes the request row and its first status event in
  one transaction. Postgres enforces the event's foreign key to the request, so
  the request row must be written first. Owner approval then adds its own event.

  Scenario: A boost request is stored with its first event on Postgres
    Given an eligible Instagram post and an empty boost store on Postgres
    When the bot requests a boost
    Then the request is pending approval and the owner is notified
    And the store holds the request and one event from none to pending approval

  Scenario: The owner approval is stored with its event on Postgres
    Given a pending boost request on Postgres
    When the owner approves it
    Then the request is approved and the store holds a second event to approved

  Scenario: The same idempotency key replays the stored request on Postgres
    Given a boost request already stored on Postgres
    When the bot sends the same request with the same idempotency key
    Then the stored request is returned and no second row or event is written
