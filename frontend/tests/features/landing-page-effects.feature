# Landing page CSS effects and responsive layout
# Ticket: AE-0003
# Plan: docs/plans/landing-page-css-effects-responsive.md

Feature: Landing page CSS effects and responsive layout

  Scenario: Homepage hero stacks on mobile with terminal first
    Given the viewport width is 375
    When I open "/"
    Then the hero terminal appears above the hero heading

  Scenario: Primary CTA has hover lift on desktop
    Given the viewport width is 1280
    When I open "/"
    And I hover the "Start Chatting" link
    Then the primary CTA has a negative translateY transform

  Scenario: Reduced motion disables hover transform
    Given reduced motion is preferred
    When I open "/"
    And I hover the "Start Chatting" link
    Then the primary CTA transform is none

  Scenario: Secondary feature card lifts on hover
    Given the viewport width is 1280
    When I open "/"
    And I scroll to the capabilities section
    And I hover the first secondary feature card
    Then that card has a negative translateY transform
