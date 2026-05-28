# Feature: Dashboard Visual Update

## Feature: Dashboard Visual Update

### Scenario: Stats grid displays correctly
Given the dashboard page is loaded
When I view the stats section
Then I see exactly 4 stat cards
And each card has an icon with color
Examples:
  | color  | value   | label          |
  | cyan   | 24      | Active Carousels |
  | magenta | 87     | Published Posts |
  | teal   | 6      | Processing    |
  | amber  | 11     | Scheduled     |

### Scenario: Quick actions show hover effects
Given I am on the dashboard page
When I hover over a quick action card
Then the card border highlights in cyan
And a subtle shadow appears
And the card transforms up 2px

### Scenario: Activity list shows recent events
Given the dashboard page is loaded
When I view the recent activity section
Then I see activity items with colored dots
And each item has title, description, and timestamp
And activity items are vertically stacked
And the first item has a green dot

### Scenario: Upcoming schedule shows scheduled items
Given the dashboard page is loaded
When I view the upcoming schedule section
Then I see scheduled items with dates and descriptions
And each item has a colored dot indicator

### Scenario: Responsive layout works on mobile
Given I am on the dashboard page
When I resize the viewport to 768px width
Then the grid becomes single column
And all content remains readable
And stat cards stack vertically

### Scenario: Focus-visible states work correctly
Given I am on the dashboard page
When I tab to the search input
Then a 2px cyan outline appears
And the outline is offset by 2px
And the outline has 4px border-radius

### Scenario: Stats data remains functional
Given the dashboard page is loaded
When I view the active carousels stat
Then the value displays statically
And the stat does not update on interaction
And no API requests are made
