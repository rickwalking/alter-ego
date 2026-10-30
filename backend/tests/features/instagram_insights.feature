Feature: Instagram insights on the dashboard (AE-0378, ADR-0021 D11)
  The dashboard shows per-post Instagram metrics for every published carousel,
  read from the Graph API at most every six hours. A metric Graph does not
  return is shown as "n/d", never estimated.

  Scenario: Fresh insights for published posts
    Given two published posts without snapshots
    When the insights are requested
    Then each post has its views, shares, saves and follows
    And the snapshots are stored

  Scenario: A recent snapshot is served without calling Graph
    Given a snapshot read two hours ago
    When the insights are requested
    Then the stored values are returned and Graph is not called

  Scenario: Graph failure keeps the last snapshot
    Given a stale snapshot and a failing Graph API
    When the insights are requested
    Then the old values are returned and marked stale

  Scenario: Missing metric
    Given the Graph API does not return follows for a post
    When the insights are requested
    Then follows is null and the card shows n/d

  Scenario: Graph refuses the metric list
    Given the Graph API refuses one metric of the list
    When the insights are requested
    Then each metric is read alone and the refused one is null

  Scenario: Ratios use only posts that report the metric
    Given one post with 3 follows and one without follows
    And 10 shares over 1000 views
    When the report is built
    Then follows per post is 3 and shares per 100 views is 1

  Scenario: No Instagram account configured
    Given no Instagram user id is set
    When the insights are requested
    Then the posts are listed from their snapshots, marked stale, and configured is false

  Scenario: Only editors read insights
    Given an anonymous caller
    When the insights are requested
    Then the answer is 401

  Scenario: Analytics flag off
    Given the editorial analytics route answers 404
    When the dashboard loads
    Then the analytics card shows the disabled state and the rest of the dashboard renders

  Scenario: The connector block reports the last sync
    Given two published posts with stored snapshots
    When the insights are requested
    Then the connector block names the instagram channel with the newest fetched_at as last sync
    And the connector is not stale and has no error

  Scenario: A stale connector says when it last synced
    Given stored snapshots older than six hours and a failing Graph API
    When the insights are requested
    Then the connector block is stale with the newest stored fetched_at and the Graph error

  Scenario: An unconfigured connector is named instead of zeros
    Given no Instagram user id is set and a published post with a stored snapshot
    When the insights are requested
    Then the connector block says instagram is not configured and last sync stays the stored one
