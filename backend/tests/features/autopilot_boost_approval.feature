Feature: Owner-approved Instagram boosts

  Scenario: Bot requests a boost and the owner approves
    Given the daily budget cap is 3000 cents
    And media is a 47-hour-old feed carousel
    When the bot posts a boost request of 2000 cents for 1 day
    Then the response is 202 with status pending_approval
    And the owner chat receives a message
    When the owner approves
    Then the request status is approved

  Scenario: Over the weekly cap
    Given 9000 cents are committed this week and the cap is 10000
    When the bot requests 2000 cents for 1 day
    Then the response is 422 weekly_cap_exceeded

  Scenario: Kill switch blocks spending
    Given BOOST_ENABLED is false and an approved request exists
    When the worker ticks
    Then no Marketing API request is made
