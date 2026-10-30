Feature: Analytics page shows channels and Instagram insights (AE-0500)
  The analytics page counts published carousels per channel, lets the reader
  switch the velocity chart between channels, and shows Instagram insights
  totals and per-post rows with the connector state instead of silent zeros.

  Scenario: The velocity chart switches between channels
    Given analytics data with per-channel velocity
    When the analytics page renders
    Then a channel picker lists all, blog and carousels
    And picking a channel filters the weekly bars and counts

  Scenario: Instagram totals match the per-post rows
    Given instagram insights with two posts and a configured connector
    When the analytics page renders
    Then the totals sum views, reach, shares, saves, follows and profile visits over the rows
    And each post row shows its metrics and when they were fetched

  Scenario: An unconfigured connector is named, not zeroed
    Given instagram insights with a connector that is not configured
    When the analytics page renders
    Then the section says the instagram connector is not configured with its last stored sync

  Scenario: The connector is named even when there are no posts
    Given instagram insights with no posts and a connector that is not configured
    When the analytics page renders
    Then the section still names the connector and says there are no posts

  Scenario: A stale connector says when it last synced
    Given instagram insights with a stale connector that failed to refresh
    When the analytics page renders
    Then the section shows the last sync time and the sync error

  Scenario: The per-post stale badge is not colour alone
    Given instagram insights with one stale post row
    When the analytics page renders
    Then the stale row carries a text badge besides its colour

  Scenario: The channel picker is keyboard accessible
    Given analytics data with per-channel velocity
    When the reader tabs to the channel picker
    Then every channel option is reachable and shows a focus ring
