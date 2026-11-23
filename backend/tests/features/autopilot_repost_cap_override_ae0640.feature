Feature: The scout can go over the weekly repost cap when the owner asks (AE-0640)
  Two repost drafts a week is the default. When Pedro explicitly asks for an
  extra repost, the scout sends override_weekly_cap and the cap is skipped.
  Every other rule still applies, and nothing publishes without Pedro's approval.

  Background:
    Given the autopilot API key is configured
    And two repost drafts were created in the last 7 days

  Scenario: Without the override the cap still refuses a third draft
    When the scout posts a third draft without override_weekly_cap
    Then the answer is 422 "weekly_cap_reached"

  Scenario: The override skips the weekly cap
    When the scout posts a third draft with override_weekly_cap true
    Then the answer is 202 with status "pending_approval"
    And the created log line records cap_override true

  Scenario: The override skips only the cap
    When the scout posts an overridden draft for a Reel published 10 days ago
    Then the answer is 422 "too_recent"

  Scenario: Drafts without the override keep their request hash
    Given a draft stored before the override field existed
    When the scout replays it with the same key and body
    Then the request hash is unchanged and the original draft is returned
    But the same body with override_weekly_cap true hashes differently

  Scenario: The request body accepts the override flag
    When the scout posts a body with override_weekly_cap
    Then it maps to the domain draft, and the flag defaults to false when missing
