Feature: Dashboard links to a carousel's public blog post
  As the site owner working on a carousel
  I want "View blog" links to open the carousel's real public post
  So that I never land on a 404 page from the dashboard

  Scenario: The workspace links the carousel's published blog post
    Given carousel "c1" has the published blog post "b1"
    When the workspace shows the published carousel preview
    Then "View Blog Post" links to "/blog/b1"

  Scenario: The workspace hides View Blog Post when the carousel has no published post
    Given carousel "c1" has no published blog post
    When the workspace shows the published carousel preview
    Then there is no "View Blog Post" link

  Scenario: After a site publish the link opens the published blog post
    Given carousel "p1" has the published blog post "b1"
    When I publish the carousel to the site
    Then "View public post" links to "/blog/b1"

  Scenario: After a site publish without a blog post the link opens the public carousel
    Given carousel "p1" has no published blog post
    When I publish the carousel to the site
    Then "View public post" links to "/carousels/p1"

  Scenario: A failed site publish shows no link
    Given the site publish fails
    When I publish the carousel to the site
    Then the error is shown without a "View public post" link
