Feature: Public blog list filtered by carousel
  As the dashboard
  I want to ask the public blog list for the post made from one carousel
  So that "View blog" links point at a real public post or are hidden

  Scenario: The public list returns the published post of one carousel
    Given a published carousel-origin post for carousel A and one for carousel B
    When I list "/api/public/blog-posts?project_id=<A>"
    Then the response holds only the post of carousel A with total 1

  Scenario: A carousel whose post is not published returns an empty list
    Given carousel C has only a draft blog post
    When I list "/api/public/blog-posts?project_id=<C>"
    Then the response is an empty list with total 0

  Scenario: A malformed carousel id is rejected
    When I list "/api/public/blog-posts?project_id=not-a-uuid"
    Then the response status is 422
