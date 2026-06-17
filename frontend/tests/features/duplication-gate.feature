Feature: Frontend duplication gate (AE-0149)
  A source-scoped copy-paste detection gate (jscpd) blocks new source
  duplication above a ratchet-down threshold, while leaving test boilerplate
  to the advisory report (AE-0151).

  Scenario: New source duplication above threshold is rejected
    Given jscpd is configured with the project source thresholds
    When two source files share a duplicated block above the threshold
    Then the duplication gate exits non-zero and reports the clone

  Scenario: Distinct source files pass the gate
    Given jscpd is configured with the project source thresholds
    When two source files share no duplicated block
    Then the duplication gate exits zero

  Scenario: Test boilerplate does not trip the blocking gate
    Given test/spec/story globs are ignored in .jscpd.json
    When duplicated setup exists only in *.test.ts files
    Then the blocking gate (npm run lint:dup over src) passes

  Scenario: The committed source duplication stays at or below the threshold
    Given the committed frontend/.jscpd.json threshold
    When jscpd runs over src
    Then the measured source duplication does not exceed the threshold
