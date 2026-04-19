Feature: Home Page

  As a visitor
  I want to see the landing page
  So that I understand what the application does

  Scenario: Display landing page with correct title
    Given I am on the home page
    Then I see the page title contains "RAG Chat"
    And I see the main heading "Chat with your Personal Knowledge Base"

  Scenario: Navigate to chat from CTA button
    Given I am on the home page
    When I click the "Start Chatting" button
    Then I am on the chat page

  Scenario: Navigate to knowledge base from CTA button
    Given I am on the home page
    When I click the "Manage Knowledge" button
    Then I am on the knowledge base page

  Scenario: Feature cards are displayed
    Given I am on the home page
    Then I see the "Intelligent Chat" feature card
    And I see the "Knowledge Management" feature card
    And I see the "AI-Powered Insights" feature card

  Scenario: Header navigation works
    Given I am on any page
    When I click the "Chat" link in the header
    Then I am on the chat page
    When I click the "Knowledge Base" link in the header
    Then I am on the knowledge base page
