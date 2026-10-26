Feature: The generation queue is visible and controllable from Telegram (AE-0523)
  The generation worker drives one carousel at a time, in strict FIFO order
  (Pedro: concurrency 1, no priorities). Pedro sees where each confirmed theme
  sits in the queue, approves several theses with one tap, retries or discards a
  run the queue parked, and keeps themes that did not fit the daily cap for the
  next morning, with a "Gerar agora" button to start one at once.

  Scenario: Confirmar shows the queue position and the estimated start
    Given a POV run waiting for its thesis and one carousel already generating
    When Pedro taps "Confirmar"
    Then the message says the thesis is confirmed with "Na fila: posição 2 de 2"
    And it shows the estimated start time in São Paulo time

  Scenario: The position counts the runs ahead in FIFO order
    Given two runs already in the queue and two confirmed runs not yet picked up
    Then the older confirmed run is third and the newer one is fourth of four

  Scenario: The start estimate uses recent drive times
    Given recent drives that took 10 and 20 minutes
    Then a run with two runs ahead is estimated to start in 30 minutes
    And without any finished drive each run ahead counts 15 minutes

  Scenario: Several waiting theses get one "Aprovar todas" message
    Given two POV runs whose thesis prompts were sent
    When the Telegram tick runs twice
    Then Pedro receives one summary listing both theses with an "Aprovar todas" button

  Scenario: "Aprovar todas" confirms every waiting thesis in FIFO order
    Given three POV runs waiting for their thesis
    When Pedro taps "Aprovar todas"
    Then the three runs are queued, oldest first
    And the summary lists each thesis with its queue position

  Scenario: "Aprovar todas" skips a thesis without a draft
    Given two runs waiting for their thesis, one without a draft thesis
    When Pedro taps "Aprovar todas"
    Then only the run with a draft is queued
    And the summary says the other one needs "Editar"

  Scenario: "Aprovar todas" confirms only the theses the summary listed
    Given a waiting thesis that arrived after the summary was sent
    When Pedro taps "Aprovar todas"
    Then that thesis stays waiting for its own confirmation

  Scenario: "Aprovar todas" twice confirms nothing new
    Given Pedro already tapped "Aprovar todas"
    When he taps it again
    Then no run changes and he is told the theses were already resolved

  Scenario: A dead-lettered run shows Retry and Discard
    Given the queue parked an autopilot run with a dead-letter reason
    When its notice is sent
    Then it explains the reason and carries "Tentar de novo" and "Descartar"

  Scenario: Retry resumes a run that died mid-generation
    Given an autopilot run escalated by a queue dead letter during generation
    When Pedro taps "Tentar de novo"
    Then the run is generating again and its generation run is queued with the failing phase reset

  Scenario: Retry restarts a run that died before it started
    Given an autopilot run failed by a queue dead letter before it started
    When Pedro taps "Tentar de novo"
    Then the run is queued again

  Scenario: Retry happens once
    Given Pedro already tapped "Tentar de novo"
    When he taps it again
    Then nothing changes and he is told it was already resolved

  Scenario: A requeued dead letter is not parked again by its old held job
    Given Pedro retried a dead letter before the dispatcher dropped its held job
    When the dispatcher runs
    Then the requeued run stays queued on its new job and the old held job is dropped

  Scenario: Retry is refused for an escalation that is not a queue dead letter
    Given an autopilot run escalated by an engine error
    When a "Tentar de novo" callback arrives for it
    Then the run stays escalated

  Scenario: Discard closes a dead-lettered run
    Given an autopilot run escalated by a queue dead letter
    When Pedro taps "Descartar"
    Then the run is rejected and nothing is queued

  Scenario: Themes over the daily cap wait in the backlog
    Given a daily cap of one and three new themes
    When the scout batch is accepted
    Then the best theme is queued and the other two are kept in the backlog

  Scenario: The backlog never holds more than 10 themes
    Given a backlog of nine themes and three new themes over the cap
    When the scout batch is accepted
    Then one more theme joins the backlog and the others are rejected as "backlog_full"

  Scenario: The next morning's slots go to the backlog first
    Given two backlog themes from earlier days and two new themes
    And a daily cap of two
    When the scout batch is accepted
    Then the two backlog themes are queued, oldest first, and the new ones wait in the backlog

  Scenario: A theme taken by "Gerar agora" during the morning intake gets one run
    Given a backlog theme that "Gerar agora" takes while the intake promotes it
    When the intake moves it out of the backlog
    Then the intake queues no second run for it

  Scenario: A theme added to the backlog today waits until tomorrow
    Given a backlog theme stored earlier today and a free slot
    When another scout batch is accepted today
    Then the backlog theme is not queued yet

  Scenario: New backlog themes are announced once with "Gerar agora"
    Given two themes that just joined the backlog
    When the Telegram tick runs twice
    Then Pedro receives one message listing them, each with a "Gerar agora" button

  Scenario: A backlog theme expires after 7 days with one note
    Given a backlog theme stored eight days ago
    When the Telegram tick runs twice
    Then the theme leaves the backlog and Pedro receives one note naming it

  Scenario: "Gerar agora" queues a backlog theme at once, outside the daily cap
    Given a backlog theme and a daily cap already used up
    When Pedro taps "Gerar agora"
    Then a queued run is created for it at the end of the queue
    And it does not count toward the daily cap

  Scenario: "Gerar agora" twice queues one run
    Given Pedro already tapped "Gerar agora" for a theme
    When he taps it again
    Then no second run is created and he is told it was already resolved

  Scenario: Waiting themes start in the morning even without a scout batch
    Given two backlog themes from earlier days and no scout batch today
    When the morning promotion runs at 08:05 São Paulo time
    Then both themes are queued, oldest first

  Scenario: The morning promotion fills only the free slots, once
    Given a daily cap of three with two runs already created today and two backlog themes
    When the morning promotion runs twice
    Then only the oldest theme is queued

  Scenario: The morning promotion is scheduled at 08:05 São Paulo time
    Given the generation worker drives autopilot runs
    Then the promotion is registered on PgQueuer's scheduler as "5 11 * * *" (UTC)
    And its maintenance mode never revives dead letters or sends a scan summary

  Scenario: Retry callback claim and recovery share one transaction
    Given Pedro's retry callback is claimed before recovery starts
    When the webhook rolls back after recovery handling
    Then the callback claim, recovery, and audit are all absent
    And the same callback can be retried successfully once
    And its audit names the application owner rather than the Telegram chat
