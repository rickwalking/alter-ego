Feature: Responsive carousel create flow (AE-0274)
  As a user creating a carousel on a small screen
  I want the create, workspace, and publish views to reflow
  So that I can work without horizontal overflow

  Scenario: Create form stacks on mobile
    Given the create page at 375px
    Then the form and the action sidebar are stacked in one column with no overflow

  Scenario: Two-pane at tablet width
    Given the create page at 768px
    Then the form and the 360px sidebar sit side by side

  Scenario: Progress steps scroll on mobile
    Given the create page at 375px
    Then the step indicator scrolls horizontally instead of clipping

  Scenario: Publish page reflows on mobile
    Given the publish page at 375px
    Then the container fits the viewport with no 960px overflow
    And the header stacks vertically

  Scenario: Workspace template and theme grids reflow
    Given the create workspace at 375px
    Then the template and theme option grids render in a single column
