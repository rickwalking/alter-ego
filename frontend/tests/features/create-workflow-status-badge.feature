Feature: Create-carousel workflow status badge
  The create-carousel flow shows workflow status through a single semantic v2
  badge (WorkflowStatusBadge over NeonBadge), so the same status looks identical
  everywhere and its colour conveys meaning. Status is read out as text + colour
  + dot, never colour alone.

  Scenario: status colour reflects state
    Given a carousel project whose workflow status is "failed"
    When the workspace renders the Project Summary
    Then the Status badge uses the red (error) variant
    And it is no longer the always-amber v1 pill

  Scenario: a live state shows a pulsing dot
    Given a project whose phase status is "in_progress"
    When the status badge renders
    Then it uses the cyan variant with a leading dot
    And the dot does not animate under prefers-reduced-motion

  Scenario: awaiting human review draws attention
    Given a project whose phase status is "awaiting_human"
    When the status badge renders
    Then it uses the magenta variant

  Scenario: ready to publish reads as a go state
    Given a project approved for publish
    When the Project Summary status badge renders
    Then it uses the teal variant labelled "Ready to publish"

  Scenario: consistent vocabulary across the flow
    Given the same status appears in the summary card and the workflow panel
    Then both render the identical WorkflowStatusBadge variant

  Scenario: unknown status falls back safely
    Given a status value not present in the map
    When resolveWorkflowStatusVisual runs
    Then it returns the default cyan variant
    And the badge label is the titlecased raw value

  Scenario: a phase name can be coloured by its run status
    Given the workflow panel shows the active phase "content"
    And the phase status is "in_progress"
    Then the badge label reads "content" with the cyan live variant
