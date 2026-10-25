Feature: The dashboard's generation queue panel API (AE-0526)
  The admin sees the generation queue (one carousel at a time, strict FIFO), the
  runs the queue parked and the backlog, and acts on them from the dashboard with
  the same rules as the Telegram buttons.

  Scenario: The board lists the active runs in FIFO order with positions
    Given a running drive and two queued drives
    When the admin loads the board
    Then the running drive is first and the queued ones follow with a start estimate

  Scenario: A parked autopilot run is listed until it is resolved
    Given a dead-lettered drive whose run is still parked and one Pedro already discarded
    When the admin loads the board
    Then only the parked one is listed, with retry and discard

  Scenario: A parked dashboard resume is listed without buttons
    Given a dead-lettered dashboard resume
    When the admin loads the board
    Then it is listed with no retry, discard or cancel

  Scenario: The backlog is listed with the day each theme expires
    Given a theme waiting in the backlog
    When the admin loads the board
    Then it is listed with its expiry seven days after it was stored

  Scenario: Retry from the panel puts the run back in the queue once
    Given a parked escalated run
    When the admin clicks retry twice
    Then the run is generating again and the second click answers 409

  Scenario: Discard from the panel closes the run
    Given a parked escalated run
    When the admin clicks discard
    Then the run is rejected

  Scenario: Cancel takes a run that has not started out of the queue
    Given a queued drive whose run has not started
    When the admin clicks cancel
    Then the drive is cancelled and the run fails with the owner's reason

  Scenario: Cancel is refused for a running drive or a dashboard resume
    Given a running drive and a queued dashboard resume
    When the admin clicks cancel on each
    Then both answer 409 and nothing changes

  Scenario: Gerar agora from the panel queues a backlog theme once
    Given a theme waiting in the backlog
    When the admin clicks Gerar agora twice
    Then one run is queued and the second click answers 409

  Scenario: An unknown run answers 404
    When the admin retries a run that does not exist
    Then the API answers 404

  Scenario: The panel API is admin only
    Given an editor
    When the editor calls any panel endpoint
    Then every call answers 403
