@AE-0509 @backend @carousels
Feature: Prompt ideas for a new cover photo
  As the owner creating a Ponto de Vista carousel
  I want "Mais ideias" to suggest prompts for a new cover photo that suit the topic and palette
  So that I can start from a good shot idea instead of a blank prompt

  Scenario: The topic and palette give three to six ideas
    Given the fast LLM answers six usable ideas
    When the owner asks for cover prompt ideas with a topic and a palette
    Then six ideas are returned
    And the prompt carries the topic and the palette colours
    And nothing is stored

  Scenario: Without a palette the model picks colours for the topic
    Given the fast LLM answers four usable ideas
    When the owner asks for cover prompt ideas with a topic and no palette
    Then four ideas are returned
    And the prompt says there is no fixed palette

  Scenario: The ideas come in the dashboard's language
    Given the fast LLM answers four usable ideas
    When the owner asks for cover prompt ideas in English
    Then the prompt asks for ideas in English

  Scenario: Unusable ideas are dropped
    Given the fast LLM answers ideas that are too short, too long, carry markup, repeat or are not text
    When the owner asks for cover prompt ideas with a topic and a palette
    Then only the usable, distinct ideas are returned, at most six

  Scenario: A short answer is asked once more
    Given the fast LLM answers two usable ideas and then three more
    When the owner asks for cover prompt ideas with a topic and a palette
    Then the ideas of both answers are returned without repeats

  Scenario: The ideas are unavailable when the LLM fails
    Given the fast LLM fails, times out, answers no JSON or fewer than three usable ideas twice
    When the owner asks for cover prompt ideas with a topic and a palette
    Then the API answers 503 cover_prompt_ideas_unavailable

  Scenario: Only the topic and the palette are accepted
    Given the owner sends a personal field, a non-hex colour or a palette name with markup
    When the owner asks for cover prompt ideas
    Then the API answers 422 and the LLM is not called

  Scenario: A too short topic is rejected
    Given a topic shorter than three characters once trimmed
    When the owner asks for cover prompt ideas
    Then the API answers 422 and the LLM is not called

  Scenario: The ideas need a logged-in editor
    Given nobody is logged in
    When cover prompt ideas are requested
    Then the API answers 401 and the LLM is not called

  Scenario: The ideas are rate limited per user
    Given the owner asked for ideas ten times this minute
    When the owner asks once more
    Then the API answers 429 while another user still gets ideas

  Scenario: The model call carries the token cap and temperature
    Given the fast chat model behind the ideas
    When the ideas completion is called
    Then the call carries the ideas' max tokens and temperature
