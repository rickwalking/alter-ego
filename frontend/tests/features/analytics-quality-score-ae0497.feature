# language: en
@AE-0497 @frontend @dashboard
Feature: The quality score tile shows real data or nothing
  Scenario: Without content scores the tile says there is no data
    Given the analytics summary has no quality score
    When the dashboard home or the analytics page is shown
    Then the quality score tile reads "Sem dados" and never "0%"

  Scenario: With content scores the tile shows the average and the count
    Given the analytics summary has an average of 70.5 from 2 scores
    When the dashboard home or the analytics page is shown
    Then the quality score tile reads "70.5%" with "2 avaliações"
