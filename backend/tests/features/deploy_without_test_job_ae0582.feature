Feature: The deploy workflow only deploys
  Tests run in PR CI (ci-gate), and main requires branches to be up to date
  before merging, so the PR's checks cover exactly what lands. The deploy
  workflow no longer re-runs the backend and frontend tests before deploying.

  Scenario: The deploy workflow has no test job and the deploy waits on nothing
    Given the deploy workflow
    Then its only job is deploy
    And the deploy job has no needs

  Scenario: The deploy keeps its main-only guard, serial concurrency and manual trigger
    Given the deploy workflow
    Then the deploy job runs only on refs/heads/main
    And deploys share the prod-deploy concurrency group without cancelling in-flight runs
    And the workflow can still be started by hand
