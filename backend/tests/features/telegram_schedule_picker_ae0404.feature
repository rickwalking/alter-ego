Feature: Pick the publish day and time on Telegram, with recommended slots (AE-0404)
  As the account owner
  I want to choose the day and then the time a carousel goes out, with the best slots marked
  So that posts go out when my audience is online, and I can move an auto-scheduled post

  # Owner report (hotfix, 2026-10-16): with AUTOPILOT_DEFAULT_PUBLISH=next_slot,
  # Approve scheduled the run straight away and the message only offered
  # "Publicar agora" and "Cancelar agendamento": the day and time could not be
  # chosen. Recommendations blend three signals per (weekday, hour) in São Paulo
  # time: the audience (Instagram online_followers), the engagement of our
  # published posts (shrunk by post count), and the plan prior (POV Tue/Thu 12:00,
  # else the 12:00/18:00/21:00 slots).

  Background:
    Given an autopilot run at final review
    And the owner chat id is on the allowlist
    And the clock is "2026-10-16 10:00" in America/Sao_Paulo (a Friday)

  # --- Reaching the picker -----------------------------------------------------

  Scenario: An auto-scheduled message offers to change the day and time
    Given AUTOPILOT_DEFAULT_PUBLISH is "next_slot"
    When the owner taps Approve
    Then the run is "scheduled" for the best recommended slot within 7 days
    And the message shows "🚀 Publicar agora", "🗓 Mudar dia/horário" and "❌ Cancelar agendamento"
    And "🗓 Mudar dia/horário" carries callback "ap:sched:<run>"

  Scenario: The review keyboard opens the same picker
    Given the run is "awaiting_owner"
    Then the review message shows "🗓 Agendar" with callback "ap:sched:<run>"
    When the owner taps "🗓 Agendar"
    Then the day keyboard is shown

  # --- Step 1: the day ---------------------------------------------------------

  Scenario: The day keyboard lists the next 7 days and stars the best ones
    When the owner taps "🗓 Agendar"
    Then the message shows 7 day buttons labelled like "Sex 16/10"
    And the first day is today because a recommended slot is still 15 minutes ahead
    And the top-ranked days carry "⭐"
    And the buttons sit 3 per row
    And each day carries callback "ap:d:<yyyymmdd>:<run>"

  Scenario: The day keyboard starts tomorrow late in the day
    Given the clock is "2026-10-16 22:00" in America/Sao_Paulo
    When the owner taps "🗓 Agendar"
    Then the first day is "Sáb 17/10"

  # --- Step 2: the time --------------------------------------------------------

  Scenario: The time keyboard shows the top 4 times, a custom time and back
    When the owner taps the day "Ter 20/10"
    Then the message shows the 4 best times of that day, each with its reason in the text
    And the best time carries "⭐"
    And it shows "✏️ Outro horário" and "← Dias"
    And "← Dias" shows the day keyboard again

  # --- Confirming --------------------------------------------------------------

  Scenario: Confirming a slot schedules an awaiting run
    Given the run is "awaiting_owner"
    When the owner picks "Ter 20/10" then "18:00"
    Then the run is "scheduled" for 20/10 18:00 São Paulo
    And the message reads "🗓 Agendado para Ter 20/10 18:00 (<reason>)"
    And it keeps the three scheduled buttons

  Scenario: Confirming a slot reschedules a scheduled run
    Given the run is "scheduled" for 20/10 12:00
    When the owner picks "Qua 21/10" then "18:00"
    Then the run is still "scheduled", now for 21/10 18:00
    And tapping the same slot again leaves the same time (idempotent)

  Scenario: The typed "Outro horário" reschedules a scheduled run
    Given the run is "scheduled" for 20/10 12:00
    When the owner taps "✏️ Outro horário" and types "21/10 19:30"
    Then the run is "scheduled" for 21/10 19:30

  Scenario Outline: A past slot or one beyond the max ahead is refused
    When the owner taps a <slot> slot button
    Then the answer says "<error>"
    And the run keeps its previous time
    And the day keyboard is shown again

    Examples:
      | slot          | error                                   |
      | past          | Esse horário já passou                  |
      | 31 days ahead | No máximo 30 dias à frente              |

  Scenario: A day outside the 7-day window is refused
    When the owner taps a day button 40 days ahead
    Then the day keyboard is shown again and nothing is scheduled

  Scenario: Every picker callback fits Telegram's 64 bytes
    Then "ap:d:<yyyymmdd>:<run>" is at most 64 bytes
    And "ap:at:<epoch>:<run>" is at most 64 bytes
    And "ap:days:<run>" is at most 64 bytes
    And a longer or malformed callback is not parsed

  # --- Recommendations ---------------------------------------------------------

  Scenario: With no insights the POV prior wins
    Given no audience data and no post insights
    And the run is a POV run
    Then the best slot is the next Tuesday or Thursday 12:00
    And its reason is "padrão do plano POV"

  Scenario: Without insights a Radar run keeps the default slots
    Given no audience data and no post insights
    Then the best slot is the next of 12:00, 18:00 or 21:00

  Scenario: With online_followers the peak hours rank first
    Given online_followers peaks at 20:00 São Paulo
    Then 20:00 ranks first on every day
    And its reason is "⭐ seus seguidores mais online"

  Scenario: Post performance shifts the ranking with shrinkage
    Given 3 published posts on Wednesdays at 15:00 with high engagement
    Then Wednesday 15:00 rises into the top 4 but stays below the prior slots
    When 30 such posts exist
    Then Wednesday 15:00 ranks first with reason "⭐ melhor engajamento (30 posts)"

  Scenario: An insights fetch error falls back silently
    Given the online_followers fetch fails
    Then the error is logged
    And the cached audience (or none) is used
    And the picker still shows recommended slots
    And the fetch is not retried for a day

  # --- No regressions ----------------------------------------------------------

  Scenario: Publicar agora, Cancelar agendamento and the due tick keep working
    Given the run is "scheduled"
    When the owner taps "🚀 Publicar agora"
    Then the run is "publishing" and the carousel is public
