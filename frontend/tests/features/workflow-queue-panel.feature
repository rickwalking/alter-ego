Feature: The generation queue panel on the workflow board (AE-0526)
  The worker generates one carousel at a time, in arrival order (Pedro: strict FIFO,
  concurrency 1). The admin sees the queue above the workflow board, retries or
  discards what the queue parked, cancels a run that has not started and starts a
  waiting theme at once.

  Scenario: The panel shows the running and queued carousels in order
    Given one carousel generating and two queued
    When the admin opens the workflow board
    Then the panel lists them by position with the phase and the estimated start

  Scenario: A parked autopilot run offers "Tentar de novo" and "Descartar"
    Given a run the queue parked
    Then its row explains the reason and offers both buttons

  Scenario: A parked dashboard run points to the editor
    Given a dashboard resume the queue parked
    Then its row links to the editor instead of offering buttons

  Scenario: A waiting theme offers "Gerar agora"
    Given a theme in the backlog
    When the admin clicks "Gerar agora"
    Then the button is posted and the panel reloads

  Scenario: A button someone else already used reloads without an error
    Given Telegram already retried the run
    When the admin clicks "Tentar de novo"
    Then the panel reloads and shows no error

  Scenario: A failed button shows an error
    When a button fails
    Then the panel says the action did not go through

  Scenario: The panel is hidden from editors
    Given the queue API answers 403
    Then no panel and no error is shown

  Scenario: A failed refresh keeps the last panel
    Given the panel loaded once
    When a refresh fails
    Then the last panel stays on screen with the load error

  Scenario: Retry waits do not invent a queue position
    Given a retry-wait row whose backend position is null
    When the panel renders
    Then no position is shown for that row

  Scenario: Running liveness uses only attributed timestamps
    Given running rows with and without a heartbeat and a queued row with stale liveness
    When the panel renders and refreshes on the board interval
    Then started time and heartbeat age appear only where their timestamps apply
    And no empty or invalid heartbeat age is shown

  Scenario: Unstaged rows use safe recovery targets
    Given projectless and project-backed unstaged rows
    When the panel renders their shared position, phase and backend ETA once
    Then generation-run-only actions remain unavailable until staging
    And a project-backed orphan reprocesses with its project version and a null run id

  Scenario: Forbidden polling terminates permanently
    Given an initial or later queue response is 403
    When its response arrives before an older successful response
    Then the board clears and interval and focus polling stop
    And the older success cannot restore the board

  Scenario: A failed refresh recovers on a later poll
    Given the panel loaded once
    When a refresh fails
    Then the last panel stays on screen with the load error
    And a later successful poll replaces the board and clears the error

  Scenario: Backend estimates remain authoritative
    Given running elapsed and retry rejoin timing are included in the backend ETA
    When the panel renders
    Then it formats that ETA without a second client estimate

  Scenario: An empty queue says so
    Given nothing is queued, parked or waiting
    Then the panel says the queue is empty
