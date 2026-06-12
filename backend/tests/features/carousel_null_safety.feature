Feature: Null-Safe Manifest Building

  Scenario: manifest_from_payload with missing optional field
    Given a payload missing the policy_version field
    When manifest_from_payload is called
    Then policy_version is None in the result

  Scenario: manifest_from_payload with invalid raw_image_hashes
    Given a payload with raw_image_hashes=None
    When manifest_from_payload is called
    Then raw_image_hashes is an empty list in the result

Feature: No Exception Suppression

  Scenario: repository without get_image_generation_by_key
    Given a repository that lacks get_image_generation_by_key
    When reuse_recorded_generation is called
    Then it returns None and logs a warning
