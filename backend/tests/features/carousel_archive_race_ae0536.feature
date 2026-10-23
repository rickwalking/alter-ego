Feature: Working on a carousel restores it even when an automatic archive raced the work
  As the site owner
  I want a carousel I am working on never to stay archived
  So that a run or an edit claimed right after an automatic archive keeps it on the board

  Scenario: The run claim restores a carousel archived after it was loaded
    Given a carousel loaded by a request
    And the idle worker archives it before the request claims the run
    When the request claims the run with the lock_version update
    Then the carousel is no longer archived

  Scenario: An edit on a carousel archived after it was loaded restores it
    Given a carousel loaded by a request
    And the idle worker archives it before the request saves an edit
    When the request saves the edit
    Then the carousel is no longer archived
