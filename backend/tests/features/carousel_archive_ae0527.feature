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
    Given my carousel whose phase is in progress
    When I archive it
    Then the archive is refused with 409 and the reason "in progress"

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

  Scenario: Active, published and in-progress carousels are not auto-archived
    Given a recently updated carousel, an idle published carousel and an idle carousel in progress
    When the workflow worker ticks
    Then none of them is archived

  Scenario: Auto-archive can be turned off
    Given the auto-archive days set to 0
    When the workflow worker ticks
    Then no carousel is archived
