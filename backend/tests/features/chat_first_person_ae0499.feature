# language: en
@AE-0499 @backend
Feature: The public chat speaks as Pedro, always in the first person
  The Alter-Ego chat is Pedro talking. Its system prompt (v4) never describes
  Pedro in the third person and tells the model never to refer to itself that way, and a deterministic
  checker flags replies that slip into "Pedro's", "he", "his alter ego" or
  "o alter ego dele". The eval runs on recorded replies, with no model call.

  Scenario: The chat agent loads the v4 prompt
    Given the Alter-Ego agent
    When it loads its system prompt
    Then it asks the registry for the alter_ego prompt at ALTER_EGO_PROMPT_VERSION
    And ALTER_EGO_PROMPT_VERSION is v4

  Scenario: The v3 prompt stays loadable for rollback
    Given the v3 prompt file
    When the registry loads alter_ego v3
    Then it returns the unchanged v3 prompt

  Scenario: The v4 prompt has no third-person reference to Pedro
    Given the v4 prompt without the two pinned lines that quote the forbidden phrases
    When it is scanned for "Pedro's", "he", "his", "him", "ele", "dele" and "his alter ego"
    Then nothing is found
    And the identity line "You are Pedro Marins" is still there

  Scenario: The v4 prompt states the first-person rule
    Given the v4 prompt
    Then it has the "SPEAKING AS YOURSELF (FIRST PERSON ONLY)" section
    And it forbids referring to itself in the third person or as "his alter ego" or "o alter ego dele"
    And it allows talking about other people in the third person
    And it answers in the user's language

  Scenario: The v4 prompt keeps every v3 rule
    Given the v4 prompt
    Then it keeps the safety, no tool disclosure, honesty and tone rules of v3
    And its vague answer about how it works is in first person

  Scenario: Recorded first-person replies pass the checker
    Given the 20 recorded eval cases in Portuguese and English
    When the checker reads each good reply
    Then no reply is flagged

  Scenario: Recorded third-person replies are flagged
    Given the 20 recorded eval cases in Portuguese and English
    When the checker reads each bad reply
    Then every reply is flagged
    And the short recorded leaks are flagged too: name as subject, "o Pedro", "his assistant", a reply opening with "He" or "Ele"

  Scenario: The eval covers identity, bot and career questions in both languages
    Given the recorded eval cases
    Then they include "Who are you?", "Quem é você?", "Is this a bot?" and "Você é um robô?"
    And half of them are in Portuguese and half in English

  Scenario: A reply that mentions someone else in the third person is not flagged
    Given a first-person reply that says "he" or "ele" about a former manager, or says "I'm Pedro"
    When the checker reads it
    Then it is not flagged

  Scenario: The prompt scan skips only the pinned quoted-phrase lines
    Given a prompt with a new third-person line inside the first-person rule section
    When it is scanned with the pinned quoted-phrase lines
    Then the new line is found
    And a pinned line that no longer matches the prompt fails the scan
