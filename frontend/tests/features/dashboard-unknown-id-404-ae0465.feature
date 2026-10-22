Feature: Dashboard pages answer 404 for unknown ids
  As the site owner following an old or mistyped dashboard link
  I want a real not-found page with HTTP 404
  So that a missing carousel or blog post is not reported as a working page

  Scenario: An unknown carousel workspace answers 404
    Given no carousel exists with id "00000000-0000-4000-8000-000000000000"
    When I open "/dashboard/create/00000000-0000-4000-8000-000000000000"
    Then the response is the not-found page with HTTP 404

  Scenario: An unknown blog post editor answers 404
    Given no blog post exists with id "00000000-0000-4000-8000-000000000000"
    When I open "/dashboard/blog-posts/00000000-0000-4000-8000-000000000000/edit"
    Then the response is the not-found page with HTTP 404

  Scenario: A malformed id answers 404 without asking the backend
    When I open "/dashboard/create/not-a-uuid"
    Then the response is the not-found page and the backend is not called

  Scenario: An existing resource renders the page
    Given the carousel exists and belongs to me
    When I open its workspace
    Then the workspace renders

  Scenario: A backend error leaves the page to show its own error
    Given the backend answers 500 or 401 for the carousel
    When I open its workspace
    Then the page renders and shows its own error or login handling

  Scenario: The blog editor's not-found and error states have a page heading
    Given the blog post cannot be loaded in the browser
    When the editor shows its not-found or error state
    Then the state has a level-1 heading
