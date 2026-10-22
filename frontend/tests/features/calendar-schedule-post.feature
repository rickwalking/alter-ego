Feature: Schedule a blog post from the calendar
  The calendar's "Schedule Post" button opens a dialog that schedules an
  approved blog post for a future local date and time through the existing
  schedule endpoint; the due-post sweep publishes it then.

  Background:
    Given I am viewing the dashboard content calendar

  Scenario: Schedule Post opens a dialog listing the approved blog posts
    Given two approved blog posts
    When I press "Schedule Post"
    Then a "Schedule a blog post" dialog opens
    And I can choose either approved post

  Scenario: Drafts are listed but must be approved first
    Given an approved post "Launch" and a draft "Ideas"
    When I open the Schedule Post dialog
    Then "Launch" can be chosen
    And "Ideas — approve it first" is listed but disabled

  Scenario: The dialog says when there is nothing to schedule
    Given no approved blog posts and no drafts
    When I open the Schedule Post dialog
    Then I see "There are no approved blog posts to schedule." with a link to the blog posts

  Scenario: The time is entered in the viewer's timezone
    When I open the Schedule Post dialog in America/Sao_Paulo
    Then the time field says "Times are in your timezone: America/Sao_Paulo"
    And the earliest selectable time is one minute from now

  Scenario: A post and a time are required
    When I press "Schedule" without choosing a post
    Then I see "Choose a post."
    When I choose a post but no time and press "Schedule"
    Then I see "Choose a date and time."
    And nothing is sent

  Scenario: A time in the past is refused before sending
    When I choose a time earlier than one minute from now
    And I press "Schedule"
    Then I see "Choose a time at least a minute from now."
    And nothing is sent

  Scenario: Scheduling an approved post sends the UTC time with the post's version
    Given the approved post "Launch" with lock version 3
    When I choose "Launch" and 2026-10-23 20:00 in America/Sao_Paulo
    And I press "Schedule"
    Then POST /api/blog-posts/<id>/schedule is sent with scheduled_publish_at "2026-10-23T23:00:00.000Z" and If-Match "3"

  Scenario: The calendar refreshes and confirms the schedule
    Given the backend accepted the schedule
    Then the dialog closes
    And the calendar is fetched again
    And I see "“Launch” is scheduled for" with the local date and time

  Scenario: Another calendar item within an hour is flagged
    Given the content calendar has "Other" at 2026-10-23 21:00 local time
    When I choose "Launch" at 2026-10-23 20:00
    Then the content calendar is read from 19:00 to 21:00
    And I see "Also on the calendar within an hour of this time: Other"
    And I can still schedule

  Scenario: The post being scheduled is not its own conflict
    Given the content calendar already has "Launch" at 2026-10-23 20:15
    When I choose "Launch" at 2026-10-23 20:00
    Then no conflict is shown

  Scenario: A post changed since the list loaded is reported
    Given the backend answers 409
    When I schedule a post
    Then I see "This post changed since the list loaded. Close the dialog and try again."

  Scenario: A post that is not ready to publish is reported
    Given the backend answers 422
    When I schedule a post
    Then I see "This post cannot be published yet: it needs content and the AI disclosure."

  Scenario: The backend refusing a past time is reported
    Given the backend answers 400 "schedule_in_past"
    When I schedule a post
    Then I see "Choose a time at least a minute from now."

  Scenario: An unexpected failure is reported
    Given the backend answers 500 or the request fails
    When I schedule a post
    Then I see "Scheduling failed. Try again."

  Scenario: Keyboard focus stays in the dialog
    When I open the Schedule Post dialog from its button
    Then focus moves into the dialog
    And Tab from the last control returns to the first
    When I press Escape
    Then the dialog closes and focus returns to "Schedule Post"

  Scenario: Cancel closes the dialog without scheduling
    When I open the Schedule Post dialog and press "Cancel"
    Then the dialog closes and nothing is sent
