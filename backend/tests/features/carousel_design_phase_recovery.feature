Feature: Design-step recovery from content-level violations
  AE-0310: a reviewer parked at the design step with blocking content-level
  presentation violations always has a working path forward — edit the
  offending slide copy in place (uncapped) or send the workflow back to the
  content phase for regeneration. The prod 38affb3e incident (slide 4 with
  drafting_scaffold_present + body_too_long discovered at design) turned every
  design revise into a silent no-op loop because the design ensure never
  re-ran presentation validation and the edit gate was content-only.

  Scenario: Reviewer edits the flagged slide in place at design
    Given a workflow parked at design with a blocking violation on slide 4
    When the reviewer submits corrected copy for slide 4 from the design step
    Then localized_slides is updated with the edited copy
    And presentation validation re-runs and reports valid
    And the design step re-renders and awaits approval without violations

  Scenario: Reviewer sends the workflow back to content from design
    Given a workflow parked at design with a blocking violation on slide 4
    When the reviewer submits a revise with target phase content and feedback
    Then the workflow re-enters the content phase with that feedback
    And slide images for unchanged outline headings are preserved

  Scenario: Plain design revise re-validates instead of looping
    Given a stored blocking validation report at the design step
    When the reviewer submits a revise without edits or target phase
    Then the design artifact re-renders and validation re-runs
    And validated_at advances past the stored report

  Scenario: Plain design revise while blocking consumes no design budget
    Given a stored blocking validation report at the design step
    When the reviewer submits a revise without edits or target phase
    Then revision_count for the design phase is not incremented
    And the fresh blocking report re-interrupts with the recovery hint

  Scenario Outline: Send-backs consume the target phase's revision budget
    Given the content phase has one revision remaining before its cap
    When the reviewer sends the workflow back to content from <source> twice
    Then the first send-back re-enters content and increments its counter
    And the second is rejected with a cap error naming the content phase

    Examples:
      | source       |
      | design       |
      | final_review |

  Scenario: Direct edits remain available after all caps are exhausted
    Given both the design and content revision caps are exhausted
    And a blocking violation is present at the design step
    When the reviewer submits corrected copy via the inline editor
    Then the edit is applied and re-validated without a cap error
    And the workflow can proceed once validation passes
