# language: en
@AE-0449 @frontend @public
Feature: The landing "Latest Posts" shows published blog posts only
  The landing section uses the same published-only public blog feed as the
  /blog list, so a draft, hidden or scheduled post never reaches the homepage
  through its public source carousel.

  Scenario: A public carousel whose blog post is a draft is not listed
    Given a public completed carousel whose blog post is still a draft
    And the public blog feed has no posts
    When a visitor opens the landing page
    Then the "Latest Posts" section shows its empty state
    And the carousel's title is not shown

  Scenario: Only published posts are listed and they open the public blog post
    Given public carousels whose blog posts are draft, hidden and scheduled
    And one published blog post
    When a visitor opens the landing page
    Then the "Latest Posts" section lists only the published post
    And its card links to the public blog post page

  Scenario: A published post card keeps one language and its own cover
    Given a published blog post made from a carousel with Portuguese and English copy
    When an English visitor opens the landing page
    Then the card title and subtitle are both English
    And the card image is the post's own cover

  Scenario: The landing page shows the empty state when the public feed fails
    Given the public blog feed is unavailable
    When a visitor opens the landing page
    Then the "Latest Posts" section shows its empty state
