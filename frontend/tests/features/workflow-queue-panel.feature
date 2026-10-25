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

  Scenario: An empty queue says so
    Given nothing is queued, parked or waiting
    Then the panel says the queue is empty
