@AE-0452 @frontend @test-infra
Feature: The shared next-intl test mock behaves like next-intl
  next-intl returns the same translator for a namespace across renders. A test
  mock that returns a new function each render re-runs every effect and
  callback that depends on `t`, which hides (or fakes) refetch loops.

  Scenario: The translator keeps its identity across renders
    Given a component that reads useTranslations for a namespace
    When it re-renders
    Then it receives the same translator function

  Scenario: An effect keyed on the translator runs once
    Given a hook whose fetch effect depends on the translator
    When it re-renders without a real change
    Then the effect has run only once
