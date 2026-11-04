Feature: Owner Retry on the workflow phase card (AE-0606)
  The carousel owner retries a failed, blocked, escalated or rejected carousel
  from its phase card at /dashboard/create/<id>. The backend capability decides
  whether the button shows; the existing full restart stays as a secondary
  "Start over". Reprocessar and Retry never show together.

  Scenario: The Retry button shows on a failed card
    Given the content phase failed and the capability says the carousel can be retried
    When the workspace renders
    Then Retry is shown inside the failed card next to Start over

  Scenario: The Retry button shows on a blocked gate
    Given the content gate is waiting for the owner and the capability says it can be retried
    When the workspace renders
    Then Retry is shown above the gate's phase content

  Scenario: The Retry button shows on a rejected carousel
    Given the system rejected the carousel and the capability says it can be retried
    When the workspace renders
    Then Retry is shown above the phase content

  Scenario: The Retry button says what it will run
    Given the capability answers a retry kind of redrive, revise or reopen
    When the button is shown
    Then the hint under it explains that kind

  Scenario: The Retry button is hidden when the capability refuses
    Given the capability answers can_retry false
    When the workspace renders
    Then no Retry button is shown

  Scenario: The Retry button is hidden when the capability cannot be read
    Given the capability read answers an error
    When the workspace renders
    Then no Retry button and no raw error are shown

  Scenario: The Retry button is hidden while Reprocessar is shown
    Given the capability says the carousel can be retried
    And the workspace shows Reprocessar for a stuck run
    When the workspace renders
    Then only Reprocessar is shown

  Scenario: The capability is read again when the carousel changes
    Given the capability was read for one lock version
    When the workflow state moves to another lock version
    Then the capability is read again for the new state

  Scenario: The capability is polled while its refusal is temporary
    Given the capability answers autopilot_active
    When the poll interval passes and the autopilot run has escalated
    Then the Retry button appears without a page reload

  Scenario: A 202 shows the accepted toast
    Given the Retry button is shown at lock version 7
    When the owner clicks Retry
    Then one POST is sent with expected_version 7
    And the accepted toast is shown
    And the workflow state is refreshed

  Scenario: The version falls back to the workflow state
    Given the capability carries no lock version and the workflow state is at lock version 7
    When the owner clicks Retry
    Then the POST is sent with expected_version 7

  Scenario: Retry stays disabled without a usable version
    Given neither the capability nor the workflow state carries a lock version
    When the button is shown
    Then it is disabled with a translated reason
    And clicking it sends nothing

  Scenario: The accepted toast outlives the button
    Given the owner's Retry was accepted
    When the capability stops offering Retry
    Then the button is gone and the accepted toast is still shown

  Scenario: A finished retry says how it ended
    Given the owner's Retry was accepted and the phase is running
    When the run finishes at a gate
    Then a finished-ok toast is shown

  Scenario: A failed retry says how it ended
    Given the owner's Retry was accepted and the phase is running
    When the run ends failed or rejected
    Then a finished-failed toast is shown

  Scenario: A reopened final review needs no finish toast
    Given the owner's Retry reopened the final review, so no run was staged
    When the workflow state refreshes
    Then only the accepted toast is shown

  Scenario: A 409 refusal shows its own text
    Given the backend refuses the Retry with a typed code
    When the owner clicks Retry
    Then a toast shows that refusal's translated text
    And the same text stays next to the button
    And the capability and the workflow state are read again

  Scenario: A refusal asking for Reprocessar refreshes the Reprocessar control
    Given the backend refuses the Retry with use_reprocess
    When the owner clicks Retry
    Then the Reprocessar capability is read again

  Scenario: An untyped failure shows a safe message
    Given the POST answers an error without a known refusal code
    When the owner clicks Retry
    Then a translated failure toast is shown without raw server details

  Scenario: A refusal text clears when the carousel changes
    Given a refusal text is shown next to the button
    When the workflow state moves to another version
    Then the text is gone

  Scenario: A double click sends one request
    Given the first Retry request is still pending
    When the owner clicks again
    Then no second request is sent

  Scenario: The pending button stays while the request runs
    Given the Retry request is pending
    When the workspace renders
    Then the button shows the pending label and is disabled
    And Start over is disabled

  Scenario: Start over still works
    Given a failed card
    When the owner clicks Start over
    Then the whole workflow restarts as before

  Scenario: The proxy forwards the retry to the backend
    Given a browser request to the retry route
    When it is a GET or a POST
    Then the backend's status and body are mirrored back
