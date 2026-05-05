Feature: Blog Subtitle i18n
  As an English-speaking visitor
  I want to see English subtitles when I select English
  So that I can understand the blog content

  Background:
    Given the blog has posts with Portuguese and English content

  Scenario: Blog listing shows English subtitle when available
    Given I am on the blog listing page
    And the locale is set to "en"
    And a post has subtitle_en "English subtitle here"
    When I view the post cards
    Then the card should show "English subtitle here"

  Scenario: Blog listing falls back to first paragraph of English content
    Given I am on the blog listing page
    And the locale is set to "en"
    And a post has no subtitle_en
    And the English blog has first paragraph "First paragraph of English content"
    When I view the post cards
    Then the card should show a truncated version of "First paragraph of English content"

  Scenario: Blog detail shows English subtitle
    Given I am on a blog post page
    And the locale is set to "en"
    And the post has English content
    When the page loads
    Then the subtitle under the title should be in English

  Scenario: Blog detail falls back to English first paragraph for subtitle
    Given I am on a blog post page
    And the locale is set to "en"
    And the post has no explicit subtitle_en
    When the page loads
    Then the subtitle should be extracted from the first paragraph of English content

  Scenario: Portuguese locale shows Portuguese subtitle
    Given I am on the blog listing page
    And the locale is set to "pt"
    When I view the post cards
    Then the card should show the Portuguese subtitle
