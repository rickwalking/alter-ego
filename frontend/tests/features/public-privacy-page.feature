Feature: Public privacy policy page
  As a visitor, or Meta reviewing the site's ads app
  I want a public privacy policy at /privacidade
  So that the site states which data it uses and how to ask about it

  Scenario: The privacy policy is public
    Given an anonymous visitor
    When they open /privacidade
    Then the page renders without a login redirect
    And the sitemap lists /privacidade

  Scenario: The privacy policy renders in Portuguese for every visitor
    Given a visitor with the site in Portuguese or in English
    When they open /privacidade
    Then the policy is shown in Portuguese, server-rendered, with its four sections

  Scenario: The only contact is the LinkedIn profile
    When a visitor reads the privacy policy
    Then the only contact offered is the LinkedIn profile
    And the page has no email address, CNPJ or postal address

  Scenario: The marketing footer links the privacy policy
    Given the landing page or the privacy page
    When the visitor reaches the footer
    Then a "Privacidade" link next to the copyright opens /privacidade
