Feature: Autopilot Instagram insights
  As the boost bot
  I want account media performance through the autopilot key
  So that I can score posts without a user login

  Scenario: Account media with rates and baselines
    Given the account has a feed carousel and a reel
    And the carousel was not published by the backend
    When the bot gets ig-insights with a valid key
    Then both posts are listed
    And the carousel has follows and a null watch time
    And the reel has watch time and null follows
    And baseline has FEED and REELS

  Scenario: Refused metric stays null
    Given Graph omits likes for a post
    When insights are refreshed
    Then likes is null

  Scenario: Missing API key
    When ig-insights is called without a key
    Then the response is 401

  Scenario: Dashboard refresh does not clear likes
    Given a snapshot already has likes
    When the dashboard insights path refreshes views and reach only
    Then likes is unchanged

  Scenario: Deprecated metrics are never requested
    When feed and reel metric sets are chosen
    Then impressions, plays and video_views are absent
