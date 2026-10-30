Feature: Analytics publishing counts per channel (AE-0500)
  "Publicados" and the publish-velocity chart count every published channel —
  blog posts and carousels published to Instagram — not only blog posts. The
  counts come from a channel-pluggable counter registry so a future channel
  (LinkedIn, TikTok) slots in without touching the aggregation.

  Scenario: Published carousels count in Publicados and the velocity chart
    Given two published blog posts and two carousels published to Instagram
    When the editorial analytics are requested
    Then published_this_week counts all four across channels
    And the summary lists a channel breakdown with blog and carousel totals
    And each velocity week carries the per-channel counts

  Scenario: A carousel published by autopilot and by manual publish counts once
    Given a carousel with both an autopilot run and a manual publish record
    When the editorial analytics are requested
    Then the carousel channel counts that carousel once

  Scenario: Carousels without an Instagram publish record do not count
    Given a completed carousel that was never published to Instagram
    When the editorial analytics are requested
    Then the carousel channel does not list it

  Scenario: An editor sees only their own carousels
    Given carousels published to Instagram owned by two different users
    When an editor requests the editorial analytics
    Then the carousel channel counts only their own carousels

  Scenario: The average_views dead field is removed
    Given published blog posts with view counts
    When the editorial analytics are requested
    Then the summary has no average_views field
    And the channel breakdown has no average_views field
