Feature: Schedule the Instagram publish from Telegram (AE-0370)
  As the account owner
  I want to publish an approved carousel now or at a good time I pick
  So that posts go out when my audience is online, without me watching the clock

  # Instagram has no native scheduling and containers expire after 24 hours,
  # so the schedule is our own queue: the time is stored on the run and the
  # containers are created only when the run is due.

  Background:
    Given an autopilot run "awaiting_owner" at final review
    And the owner chat id is on the allowlist
    And the clock is "2026-10-15 10:00" in America/Sao_Paulo

  # --- Approve -----------------------------------------------------------------

  Scenario: Approve offers publish now or schedule
    Given AUTOPILOT_DEFAULT_PUBLISH is "now"
    When the owner taps Approve
    Then the message shows "🚀 Publicar agora" with callback "ap:pubnow:<run>"
    And it shows "🗓 Agendar" with callback "ap:sched:<run>"
    And every callback is at most 64 bytes
    And the run is still "awaiting_owner"

  Scenario: Publish now keeps today's approve behaviour
    When the owner taps "🚀 Publicar agora"
    Then final review is approved
    And the run is "publishing" and the carousel is public
    And the worker publishes the carousel and its Story and sends the notice

  Scenario: A refused editorial approve keeps the review open
    Given the editorial approve is refused
    When the owner taps "🚀 Publicar agora"
    Then the run is "awaiting_owner"
    And the review keyboard is shown again

  # --- Slots -------------------------------------------------------------------

  Scenario: Agendar lists the next three slots and a custom time
    When the owner taps "🗓 Agendar"
    Then the buttons are "hoje 12:00", "hoje 18:00", "hoje 21:00"
    And a "✏️ Outro horário" button is shown

  Scenario: A slot less than 15 minutes away is skipped
    Given the clock is "2026-10-15 11:50" in America/Sao_Paulo
    When the next three slots are computed
    Then they are "15/10 18:00", "15/10 21:00", "16/10 12:00"

  Scenario: Slots roll over to the next day
    Given the clock is "2026-10-15 22:00" in America/Sao_Paulo
    When the next three slots are computed
    Then they are "16/10 12:00", "16/10 18:00", "16/10 21:00"

  Scenario: Slots are computed in America/Sao_Paulo, whatever the server zone
    Given the clock is "2026-10-15 14:00" in UTC
    When the next three slots are computed
    Then the first slot is "15/10 18:00" in America/Sao_Paulo

  # --- Choosing a time ---------------------------------------------------------

  Scenario: Choosing a slot schedules the run
    When the owner taps the "hoje 18:00" slot
    Then final review is approved and the workflow is "approved_for_publish"
    And the carousel is not public yet
    And the run is "scheduled" with scheduled_at "2026-10-15 18:00" America/Sao_Paulo
    And the message reads "🗓 Agendado para 15/10 18:00"
    And it shows "🚀 Publicar agora" and "❌ Cancelar agendamento"

  Scenario: A double tap schedules once
    When the owner taps the "hoje 18:00" slot twice
    Then the editorial approve runs once
    And the second tap answers "already handled"

  Scenario: Outro horário asks for a time with ForceReply
    When the owner taps "✏️ Outro horário"
    Then a ForceReply asks for "HH:MM" or "DD/MM HH:MM" in America/Sao_Paulo

  Scenario Outline: The owner types a valid time
    Given the owner tapped "✏️ Outro horário"
    When the owner replies "<text>"
    Then the run is "scheduled" for "<local>"

    Examples:
      | text        | local       |
      | 19:30       | 15/10 19:30 |
      | 09:15       | 16/10 09:15 |
      | 20/10 08:00 | 20/10 08:00 |

  Scenario Outline: The owner types an invalid time
    Given the owner tapped "✏️ Outro horário"
    When the owner replies "<text>"
    Then the run is still "awaiting_owner"
    And the reply says "<reason>"
    And the ForceReply is asked again

    Examples:
      | text        | reason                                  |
      | amanhã      | Use HH:MM ou DD/MM HH:MM                |
      | 25:00       | Use HH:MM ou DD/MM HH:MM                |
      | 31/02 10:00 | Use HH:MM ou DD/MM HH:MM                |
      | 15/10 09:00 | Esse horário já passou                  |
      | 20/12 10:00 | No máximo 30 dias à frente              |

  # --- Worker tick -------------------------------------------------------------

  Scenario: A due run publishes at its time
    Given the run is "scheduled" for "15/10 18:00"
    When the worker ticks at "15/10 17:59"
    Then nothing is published
    When the worker ticks at "15/10 18:00"
    Then the run moves "scheduled" to "publishing" with reason "schedule_due"
    And the carousel is released public
    And the carousel and its Story are published once
    And the notice has no delay line

  Scenario: A late run publishes anyway and says how late
    Given the run is "scheduled" for "15/10 18:00"
    When the worker ticks first at "15/10 18:25" after a deploy
    Then the carousel is published
    And the notice says "(publicado com atraso de 25 min)"

  Scenario: A due tick never publishes twice
    Given the run was published by the schedule
    When the worker ticks again
    Then no Graph call is made

  Scenario: A scheduled carousel that is no longer approved expires
    Given the run is "scheduled" and the carousel was rejected
    When the worker ticks after the scheduled time
    Then the run is "expired" with reason "schedule_withdrawn"
    And nothing is published

  Scenario: The 72 h review expiry never expires a scheduled run
    Given the run was "scheduled" 80 hours ago for a time in the future
    When the runner sweeps expiries
    Then the run is still "scheduled"

  # --- Cancel and publish now while scheduled ----------------------------------

  Scenario: Cancel returns the run to the review
    Given the run is "scheduled"
    When the owner taps "❌ Cancelar agendamento"
    Then the run is "awaiting_owner" and scheduled_at is cleared
    And the normal review keyboard is shown again

  Scenario: Publish now while scheduled publishes immediately
    Given the run is "scheduled"
    When the owner taps "🚀 Publicar agora"
    Then the run is "publishing" and the carousel is public
    And scheduled_at is cleared, so no delay line is added

  # --- Default mode ------------------------------------------------------------

  Scenario: next_slot mode schedules the next slot directly
    Given AUTOPILOT_DEFAULT_PUBLISH is "next_slot"
    When the owner taps Approve
    Then the run is "scheduled" for "15/10 12:00"
    And the message reads "🗓 Agendado para 15/10 12:00"
    And it shows "🚀 Publicar agora" and "❌ Cancelar agendamento"

  # --- Safety ------------------------------------------------------------------

  Scenario: A non-owner cannot schedule or cancel
    Given a chat id that is not on the allowlist
    When it taps a slot or "❌ Cancelar agendamento"
    Then the run is unchanged and nothing is sent

  Scenario: Schedule, then the due tick, on the real engine
    Given the real editorial engine with fake Graph and Telegram
    When the owner schedules "15/10 18:00" and the worker ticks at "15/10 18:00"
    Then the run is "published" and one Story was posted
