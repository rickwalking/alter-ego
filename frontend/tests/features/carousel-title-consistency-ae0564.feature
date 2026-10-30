Feature: Carousel display title consistency
  As the site owner working on a carousel
  I want the workspace breadcrumb, publish breadcrumb, publish heading and
  workspace preview to show the same carousel name
  So that I never see two different titles for the same carousel

  Scenario: Publish breadcrumb and heading agree when the title is set
    Given carousel "p1" has the title "AI Guide" and the topic "AI topic"
    When the owner opens the publish page
    Then the sticky-header breadcrumb shows "AI Guide"
    And the page heading shows "AI Guide"

  Scenario: Publish breadcrumb and heading fall back to the topic
    Given carousel "p1" has a blank title and the topic "AI topic"
    When the owner opens the publish page
    Then the sticky-header breadcrumb shows "AI topic"
    And the page heading shows "AI topic"

  Scenario: Workspace breadcrumb uses the same display title
    Given carousel "p1" has the title "AI Guide" and the topic "AI topic"
    When the owner opens the create workspace
    Then the workspace breadcrumb shows "AI Guide"

  Scenario: Workspace breadcrumb falls back to the topic
    Given carousel "p1" has a blank title and the topic "AI topic"
    When the owner opens the create workspace
    Then the workspace breadcrumb shows "AI topic"

  Scenario: The workspace preview uses the same display title
    Given carousel "p1" has the title "**Bold** Moves" and the topic "AI topic"
    When the workspace shows the carousel preview
    Then the preview heading shows "Bold Moves"
