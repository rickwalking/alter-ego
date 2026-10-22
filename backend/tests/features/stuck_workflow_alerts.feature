Feature: Stuck workflow alerts fire once per stuck episode

  The workflow worker checks every minute for carousel projects that stopped
  moving. A stuck episode starts at the project's last update; each episode
  alerts the admins once, and the log stays quiet while nothing is new.

  Scenario: A stuck project alerts once per stuck episode
    Given a carousel project not updated for more than 48 hours
    When the workflow worker checks the project on several runs, hours apart
    Then one stuck_workflow log line and one notification per admin are emitted on the first run
    And the later runs emit no log line and no notification

  Scenario: A project that moves and gets stuck again alerts again
    Given a stuck project whose admins were already alerted
    When the project changes phase and then stays unchanged for more than 48 hours
    Then the next run alerts the admins again for the new stuck episode

  Scenario: Already alerted stuck projects keep the log quiet
    Given 15 stuck projects whose admins were already alerted in this episode
    When the workflow worker runs
    Then no alert is emitted and no stuck_workflow log line is written

  Scenario: Other notifications for the project do not silence a stuck alert
    Given a stuck project with a deadline reminder created during the stuck episode
    When the workflow worker runs
    Then the admins are alerted that the project is stuck

  Scenario: A stalled in-progress run alerts once per stall
    Given a carousel run in progress that has not been updated for more than 30 minutes
    When the workflow worker checks it on several runs
    Then one stuck_workflow alert is emitted on the first run and none on the later runs
