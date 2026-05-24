Feature: Persona Profile Management
  As a content creator
  I want to define and refine my writing persona
  So that AI-generated content matches my authentic voice

  Background:
    Given I am logged in as "Pedro"

  Scenario: Create persona from writing samples
    When I navigate to "Persona Settings"
    And I enter persona name "Pedro's Professional Voice"
    And I upload 5 writing samples:
      | sample_title                    | file              |
      | "LinkedIn Post - AI Ethics"     | "sample1.txt"     |
      | "Blog - Startup Lessons"        | "sample2.txt"     |
      | "Twitter Thread - Security"     | "sample3.txt"     |
      | "Newsletter - May 2026"         | "sample4.txt"     |
      | "Conference Talk Transcript"    | "sample5.txt"     |
    And I click "Analyze Voice"
    Then the AI should analyze the samples and extract:
      | attribute                     | value                                      |
      | tone                          | "conversational, confident, occasionally humorous" |
      | sentence_length               | "Short punchy sentences (avg 12 words)"     |
      | paragraph_structure           | "1-3 sentences per paragraph"               |
      | opinion_expression            | "Strong opinions, loosely held"             |
      | common_phrases                | ["Here's the thing", "What most people miss"] |
      | forbidden_patterns            | ["In today's world", "Let's dive in"]       |
    And I should see a persona preview with sample rewrite

    When I adjust the "formality" slider to 0.3
    Then the sample rewrite should update in real-time
    And it should sound less formal

    When I click "Save Persona"
    Then the persona should be saved
    And I should see "Persona 'Pedro's Professional Voice' created"

  Scenario: Persona feedback loop
    Given I have a persona "Pedro's Professional Voice"
    And I generated a carousel with AI
    When I edit slide 2 and replace:
      | original                         | replacement                                    |
      | "AI is transforming industries"    | "AI isn't just changing industries — it's eating them alive" |
    And I click "This edit improves the voice match"
    Then the system should record this as a positive example
    And future AI outputs should lean toward:
      | pattern          | example                              |
      | strong_opinions  | "isn't just... it's eating them alive" |
      | vivid_language   | "eating them alive"                    |

    When I generate another carousel
    Then the AI should use more vivid language and strong opinions

  Scenario: Voice match scoring
    Given I have a persona "Pedro's Professional Voice"
    When I paste text: "In today's world, AI is transforming how we work. Let's dive into the details."
    And click "Check Voice Match"
    Then I should see a score of "23/100"
    And I should see specific issues:
      | issue                    | suggestion                          |
      | "In today's world"       | "Remove — it's a forbidden phrase"  |
      | "Let's dive into"        | "Replace with 'Here's what actually matters'" |
      | "transforming how we work"| "Too neutral — add Pedro's opinion" |
    And I should see a rewritten version that scores "91/100"
