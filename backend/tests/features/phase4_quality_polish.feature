Feature: Phase 4 Quality and Polish
  As a content creator
  I want quality checks, SEO analysis, and editorial audit
  So that I publish professional, accessible, original content

  Background:
    Given I am logged in as an editor

  Scenario: SEO analysis returns score and issues
    Given a blog post exists with title "AI Security"
    When I request SEO analysis for the post
    Then the response should include an overall_score
    And the response should include issues or suggestions

  Scenario: Accessibility check detects missing alt text
    Given a blog post exists with a featured image but no alt text
    When I request accessibility check for the post
    Then the response should include a missing alt text issue

  Scenario: Plagiarism check compares against sources
    Given a blog post exists with source materials
    When I run plagiarism check on the post
    Then the response should include overall_score and passed fields

  Scenario: AI disclosure label reflects AI usage
    Given a blog post has AI suggestions applied
    When I request AI disclosure for the post
    Then the label should not be "none"

  Scenario: Editorial audit logs content updates
    Given a blog post exists
    When I update the blog post title
    Then an audit event should be recorded for the update

  Scenario: Blog post list supports search and pagination
    Given multiple blog posts exist
    When I list blog posts with search query and limit
    Then the response should include paginated items and total count

  Scenario: Editorial analytics returns velocity metrics
    When I request editorial analytics
    Then the response should include content_velocity_per_week
    And the response should include quality_score_average
