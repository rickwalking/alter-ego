Feature: Repost drafts and the owner's Telegram decision (AE-0628)
  The scout submits a repost draft; nothing is published until Pedro approves.

  Background:
    Given the autopilot API key is configured
    And a Reel published 120 days ago with 3 collaborators-free metadata

  Scenario: A valid draft is accepted
    When the scout posts a draft with an Idempotency-Key
    Then the answer is 202 with status "pending_approval", a preview_url and expires_at 12 hours later

  Scenario: The same key and body replay the original response
    Given a draft created with key "scout-2026-11-19"
    When the scout posts the same body with the same key
    Then the original draft is returned and no second draft exists

  Scenario: The same key with a different body conflicts
    When the scout posts a different body with a used key
    Then the answer is 409 "idempotency_conflict"

  Scenario Outline: Field rules answer 400 invalid_field
    When the scout posts a draft whose <field> is <problem>
    Then the answer is 400 "invalid_field" with field "<field>"

    Examples:
      | field                  | problem                          |
      | Idempotency-Key        | missing or 7 characters          |
      | caption                | empty, 2201 chars, 31 hashtags   |
      | hook_text              | 91 characters                    |
      | hook_duration_s        | 0 or 4.5                         |
      | trim_end_s             | before trim_start_s              |
      | trim_end_s             | a final video of 2 s or 95 s     |
      | reason                 | 9 characters                     |
      | collaborators          | 4 names or "@bad name"           |
      | publish_window.latest  | before earliest or in the past   |

  Scenario: A foreign id or a non-Reel is not found
    When the scout posts a draft for a feed post or a foreign media id
    Then the answer is 404 "reel_not_found"

  Scenario: A Reel younger than 60 days is too recent
    When the scout posts a draft for a Reel published 30 days ago
    Then the answer is 422 "too_recent"

  Scenario: A Reel with a live repost in 90 days is refused
    Given a pending repost of the Reel created 10 days ago
    When the scout posts another draft for it
    Then the answer is 409 "already_reposted"

  Scenario: The weekly cap
    Given two drafts created in the last 7 days
    When the scout posts a third
    Then the answer is 422 "weekly_cap_reached"
    But a failed draft does not count toward the cap

  Scenario: A cover must be a fresh, unused reel cover
    When the scout names a carousel cover, an expired cover or a used cover
    Then the answer is 422 "asset_invalid"
    And a valid reel cover is claimed by the draft

  Scenario: Collaborators default to the original Reel's
    When the draft has no collaborators
    Then the draft stores the original Reel's collaborators

  Scenario: GET /repost/{id} and GET /reposts
    Given two drafts
    Then GET /repost/{id} returns the draft's status
    And GET /reposts?status=pending_approval returns them newest first
    And an unknown id answers 404 "repost_not_found"

  Scenario: Aprovar schedules the best slot in the window
    Given a previewed pending draft with a publish window
    When the owner taps Aprovar
    Then the draft is approved with cover_choice "grok" and publish_at inside the window

  Scenario: Aprovar without a window publishes now
    When the owner taps Aprovar on a draft without a window
    Then publish_at is the approval time

  Scenario: Usar capa original approves with the original cover
    When the owner taps Usar capa original
    Then the draft is approved with cover_choice "original"

  Scenario: Rejeitar rejects
    When the owner taps Rejeitar
    Then the draft is rejected and the prompt says so

  Scenario: Editar legenda replaces the caption from the owner's next text
    When the owner taps Editar legenda and sends a new caption
    Then the draft keeps pending_approval with the new caption and the prompt is refreshed
    But a caption with 31 hashtags is refused and the draft keeps waiting

  Scenario: A tap after expiry or after a decision does nothing
    When the owner taps a button on an expired, decided or unrendered draft
    Then the draft does not change and the tap is answered as gone
