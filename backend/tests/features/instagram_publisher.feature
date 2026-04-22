Feature: Instagram carousel publishing via Meta Graph API
  As a carousel author
  I want to publish a completed carousel to my Instagram account
  So I don't have to upload slides manually

  Background:
    Given META_IG_ACCESS_TOKEN and META_IG_USER_ID are configured
    And the carousel has 4 image URLs reachable over public HTTPS

  Scenario: Happy path — 4 item containers, 1 parent, publish
    When publish_instagram is called with caption + image_urls
    Then 4 item containers are created with is_carousel_item=true
    And one parent CAROUSEL container is created with children=<child_ids>
    And the parent is polled until status_code=FINISHED
    And media_publish is called with the parent creation_id
    And the result status is "published" with a post_id

  Scenario: Missing access token surfaces an actionable error
    Given META_IG_ACCESS_TOKEN is empty
    When publish_instagram is called
    Then the result status is "failed"
    And the error_message mentions META_IG_ACCESS_TOKEN

  Scenario: Fewer than 2 images is rejected before any API call
    When publish_instagram is called with 1 image_url
    Then no HTTP request is sent
    And the result status is "failed" mentioning "at least 2"

  Scenario: More than 10 images is rejected before any API call
    When publish_instagram is called with 11 image_urls
    Then no HTTP request is sent
    And the result status is "failed" mentioning "at most 10"

  Scenario: Container stays in ERROR → publish fails with clear message
    When the parent container polls as status_code=ERROR
    Then publish_instagram returns failed
    And the error_message mentions the container status ERROR

  Scenario: HTTP 4xx from Meta is surfaced, not raised
    Given Meta returns 400 on item container creation
    When publish_instagram is called
    Then the result status is "failed"
    And the error_message mentions "Instagram API"
