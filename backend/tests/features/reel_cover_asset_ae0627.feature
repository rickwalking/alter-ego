Feature: Reel covers on POST /api/autopilot/assets (AE-0627)
  GrokBot uploads a 1080x1920 cover for a repost draft through the same asset
  route as carousel covers, with purpose=reel_cover.

  Scenario: An upload without purpose stays a carousel cover
    Given an ai_image of 1080x1350
    When it is uploaded without a purpose
    Then the answer is 201 with purpose "carousel_cover" and size 1080x1350

  Scenario: A 9:16 reel cover is accepted at 1080x1920
    Given an ai_image of 1080x1920
    When it is uploaded with purpose "reel_cover"
    Then the answer is 201 with purpose "reel_cover" and size 1080x1920

  Scenario: A larger 9:16 reel cover is scaled, never cropped
    Given an ai_image of 1440x2560
    When it is uploaded with purpose "reel_cover"
    Then it is stored at exactly 1080x1920

  Scenario: A reel cover that is not 9:16 is refused
    Given an ai_image of 1080x1350
    When it is uploaded with purpose "reel_cover"
    Then the answer is 422 "asset_ratio_invalid"

  Scenario: A reel cover smaller than 1080x1920 is refused
    Given an ai_image of 720x1280
    When it is uploaded with purpose "reel_cover"
    Then the answer is 422 "asset_too_small"

  Scenario: A screenshot cannot be a reel cover
    When a screenshot is uploaded with purpose "reel_cover"
    Then the answer is 422 "asset_kind_invalid"

  Scenario: An unknown purpose is refused
    When an ai_image is uploaded with purpose "story_cover"
    Then the answer is 422 "asset_purpose_invalid"

  Scenario: A topic cannot use a reel cover
    Given a stored reel cover
    When a carousel topic names it as its cover
    Then the topic is refused with "cover_asset_unknown"

  Scenario: The sweep keeps a cover a repost claimed
    Given a reel cover older than 6 hours claimed by a repost draft
    When the cover sweep runs
    Then the cover is not deleted
