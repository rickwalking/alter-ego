@AE-0452 @frontend @backend
Feature: Calendar entries keep their content type
  The content calendar API labels each entry "blog_post" or "carousel". The
  calendar shows blog posts with the blog colour and label, and the frontend
  mapping follows the values the API publishes in its OpenAPI schema.

  Scenario: A blog post entry shows as a blog
    Given the calendar API returns an entry with content type "blog_post"
    When the calendar builds its days
    Then the entry's content type is "blog"

  Scenario: A carousel entry shows as a carousel
    Given the calendar API returns an entry with content type "carousel"
    When the calendar builds its days
    Then the entry's content type is "carousel"

  Scenario: The frontend mapping matches the published API values
    Given the OpenAPI schema of the calendar item lists its content types
    Then the frontend maps exactly those values
