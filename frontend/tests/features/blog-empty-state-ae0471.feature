Feature: Visitors see a visitor-facing empty blog
  As a visitor opening the blog before any article is published
  I want a message meant for me and somewhere to go next
  So that I am not told to "generate one with AI", which only the owner can do

  Scenario: The empty blog speaks to visitors and links the carousels
    Given no blog post is published
    When I open "/blog"
    Then I read that no articles are published yet
    And I get a link to the visual carousels
    And no owner instruction such as "Generate one with AI" is shown

  Scenario: The empty-state copy exists in both languages without owner instructions
    Then the English and Portuguese empty-blog messages mention no generation or carousel creation
