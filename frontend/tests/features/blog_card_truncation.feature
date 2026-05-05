Feature: Blog Card Subtitle Truncation
  As a visitor
  I want card subtitles to be concise
  So that the card layout is not broken by long text

  Background:
    Given the blog has posts with long subtitles

  Scenario: Homepage card shows truncated subtitle in English
    Given I am on the homepage
    And the locale is set to "en"
    When I view the latest posts section
    Then each card subtitle should contain at most 15 words
    And each card subtitle should end with "..."

  Scenario: Homepage card shows truncated subtitle in Portuguese
    Given I am on the homepage
    And the locale is set to "pt"
    When I view the latest posts section
    Then each card subtitle should contain at most 15 words
    And each card subtitle should end with "..."

  Scenario: Blog listing card shows truncated subtitle
    Given I am on the blog listing page
    And the locale is set to "en"
    When I view the post cards
    Then each card subtitle should contain at most 15 words
    And each card subtitle should end with "..."

  Scenario: Short subtitle is not truncated
    Given a post has a subtitle with 10 words
    When I view the card for that post
    Then the subtitle should show all 10 words
    And the subtitle should not end with "..."

  Scenario: Subtitle with markdown is stripped before truncation
    Given a post has a subtitle containing "**bold** text and more words here"
    When I view the card for that post
    Then the markdown syntax should not appear in the subtitle
    And the subtitle should contain at most 15 words
