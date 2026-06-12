Feature: Checkpoint fixture portability
  The captured carousel checkpoint must deserialize with LangGraph's
  default serializer alone, proving package moves cannot strand
  persisted workflow state (AE-0075).

  Scenario: Captured checkpoint deserializes without project imports
    Given a sanitized checkpoint fixture captured from the carousel workflow
    When the fixture is deserialized using only LangGraph's default serializer
    Then deserialization succeeds
    And no project-specific class import is required

  Scenario: Class-path-dependent payload is detected and reported
    Given a checkpoint fixture containing a non-primitive serialized value
    When the portability scan runs
    Then the scan reports the offending key path
