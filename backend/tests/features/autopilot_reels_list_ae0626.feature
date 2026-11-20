Feature: GET /api/autopilot/reels for the repost scout (AE-0626)
  The scout lists Pedro's past Reels with metrics, rates, a baseline and repost
  history, and can stream a Reel's MP4 without an expiring CDN URL.

  Background:
    Given the autopilot API key is configured
    And Graph lists Reels, feed posts and Stories for the account

  Scenario: Only Reels inside the age window are listed
    Given Reels published 30, 90 and 800 days ago
    When the scout calls GET /reels with the defaults
    Then only the 90-day-old Reel is returned

  Scenario: Reels are sorted by views by default
    Given two eligible Reels with 500 and 9000 views
    When the scout calls GET /reels
    Then the 9000-view Reel comes first

  Scenario: Sorting by shares rate and by timestamp
    When the scout calls GET /reels with sort=shares_rate_desc or sort=timestamp_desc
    Then the order follows shares per 100 views or the newest first

  Scenario: Paging with an opaque cursor
    Given three eligible Reels
    When the scout calls GET /reels with limit=2
    Then two items and a next_cursor are returned
    And the next_cursor returns the third Reel and no next_cursor

  Scenario: Rates, watch ratio and baseline
    Given a Reel with 1000 views, 50 shares, 4500 ms average watch time and 9 s duration
    Then shares_per_100_views is 5.0 and avg_watch_ratio is 0.5
    And the baseline holds the median views of the window

  Scenario: A stale snapshot is refreshed, a failed refresh is marked stale
    Given a Reel whose insight snapshot is older than 6 hours
    When Graph answers the insights read
    Then the item has fresh metrics and stale false
    But when Graph fails the read the item keeps the old metrics with stale true

  Scenario: Durations and collaborators are probed once and cached
    Given a Reel with no cached facts
    When the scout calls GET /reels twice
    Then ffprobe and the collaborators edge are called once

  Scenario: Reposted Reels are hidden
    Given a Reel with a pending repost created 10 days ago
    And a Reel that is itself a published repost
    When the scout calls GET /reels with exclude_reposted_days=90
    Then neither Reel is listed
    But with exclude_reposted_days=0 the original Reel is listed with its last_repost

  Scenario: A bad query parameter is refused
    When the scout calls GET /reels with limit=500
    Then the answer is 400 with code "invalid_field" and field "limit"

  Scenario: Instagram is not configured
    Given no Instagram user id
    When the scout calls GET /reels
    Then the answer is 503 "instagram_not_configured"

  Scenario: The video route streams the MP4
    When the scout calls GET /reels/{media_id}/video for one of Pedro's Reels
    Then the answer is 200 video/mp4 with the CDN bytes

  Scenario: The video route refuses other media
    When the scout calls GET /reels/{media_id}/video for a feed post or a foreign id
    Then the answer is 404 "reel_not_found"
