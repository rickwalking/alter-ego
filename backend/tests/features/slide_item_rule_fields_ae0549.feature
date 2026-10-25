Feature: Checklist rule violations point at the item that needs the fix
  The editor shows a violation under the field it names. A too-short summary or
  closing list used to be reported on the slide body, so the owner looked for it
  in the wrong place; and a checklist item body cut off mid-sentence passed.

  Scenario: A missing summary point is reported on the first incomplete item
    Given a summary slide whose second point has a title but no body
    When the slide is validated
    Then summary_points_missing is reported on summary_points[1].body

  Scenario: Too few complete summary points are reported on the list
    Given a summary slide with two complete points
    When the slide is validated
    Then summary_points_missing is reported on summary_points

  Scenario: A closing slide with too few actions points at the first incomplete action
    Given a closing slide whose first action has no title
    When the slide is validated
    Then closing_actions_missing is reported on actions[0].title

  Scenario: A checklist item body cut off mid-sentence is truncated copy
    Given a summary point body that ends "telefone. Não é" or on a dangling connector or an ellipsis
    When the slide copy is checked
    Then copy_truncated is reported on that item body

  Scenario: A short checklist fragment without a full stop is not truncated
    Given a summary point body "Revisão automática de PRs"
    When the slide copy is checked
    Then no copy_truncated is reported on it
