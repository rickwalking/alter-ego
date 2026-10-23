Feature: The owner archives a stale carousel and idle carousels archive themselves
  As the site owner
  I want to close carousels I gave up on, and have long-idle ones closed for me
  So that the workflow board and the alerts only show work that is alive

  Scenario: The owner archives a stale carousel
    Given my carousel waiting for review for days
    When I archive it
    Then it is archived and leaves the active workflow board
    And it is listed on the archived board

  Scenario: Archiving twice keeps the first archive time
    Given my archived carousel
    When I archive it again
    Then it stays archived with its first archive time

  Scenario: The owner restores an archived carousel
    Given my archived carousel
    When I restore it
    Then it is back on the active workflow board and no longer archived

  Scenario: A carousel in progress cannot be archived
    Given my carousel whose phase run is live (its heartbeat is recent)
    When I archive it
    Then the archive is refused with 409 and the reason "in progress"

  Scenario: A phase stuck with a stale heartbeat can be archived
    Given my carousel whose phase is in progress but its heartbeat is stale
    When I archive it
    Then it is archived

  Scenario: A carousel an autopilot run still needs cannot be archived
    Given my carousel with an autopilot run that is scheduled to publish
    When I archive it
    Then the archive is refused with 409 and the reason "autopilot"

  Scenario: A run that starts before the write keeps the carousel
    Given my carousel that starts a phase run after the access check
    When the archive write runs
    Then it re-checks the rules and archives nothing

  Scenario: A published carousel cannot be archived
    Given my published carousel
    When I archive it
    Then the archive is refused with 409 and the reason "published"

  Scenario: Someone else's carousel cannot be archived or restored
    Given a carousel of another editor
    When I archive or restore it
    Then the request is refused with 403
    And an admin can archive and restore it

  Scenario: An unknown carousel cannot be archived
    When I archive a carousel that does not exist
    Then the request is refused with 404

  Scenario: An archived carousel raises no alerts
    Given an archived carousel stuck for days and an archived failed carousel
    When the workflow alerts run
    Then no alert is raised for either

  Scenario: An idle carousel is archived automatically
    Given a carousel not updated for more than the auto-archive days
    When the workflow worker ticks
    Then it is archived

  Scenario: A carousel an autopilot run still needs is not auto-archived
    Given an idle carousel with an autopilot run that is scheduled, publishing or waiting for the owner
    When the workflow worker ticks
    Then it is not archived

  Scenario: Working on an archived carousel brings it back to the board
    Given my archived carousel
    When a phase run starts on it or I edit it
    Then it is no longer archived
    And a failed or reaped run alone keeps it archived

  Scenario: The board says who may archive a card and why not
    Given my carousel, a carousel I only review, and a carousel with a live run
    When I open the workflow board
    Then my carousels can be archived and the reviewed one cannot
    And the live one says why it cannot be archived now

  Scenario: Active, published and in-progress carousels are not auto-archived
    Given a recently updated carousel, an idle published carousel and an idle carousel in progress
    When the workflow worker ticks
    Then none of them is archived

  Scenario: Auto-archive can be turned off
    Given the auto-archive days set to 0
    When the workflow worker ticks
    Then no carousel is archived
