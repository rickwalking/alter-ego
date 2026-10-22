@AE-0452 @frontend @public
Feature: The sitemap and robots.txt describe the real public site
  Search engines read robots.txt and sitemap.xml. Both use the production
  domain and the sitemap lists published content only.

  Scenario: robots.txt points at the production sitemap
    When robots.txt is generated
    Then its sitemap URL is "https://marinssolutions.com/sitemap.xml"

  Scenario: The sitemap lists the public pages on the production domain
    When the sitemap is generated
    Then it lists the home page, the blog list, the carousel gallery and the public chat under "https://marinssolutions.com"
    And it lists no dashboard page

  Scenario: The sitemap lists every published post and public carousel
    Given a published blog post and a public completed carousel
    When the sitemap is generated
    Then it lists the post's public blog URL with its publication date
    And it lists the carousel's public viewer URL

  Scenario: The sitemap still renders when the content feeds are unavailable
    Given the public blog feed is unavailable
    When the sitemap is generated
    Then it lists only the public pages

  Scenario: A carousel share image uses the production domain
    Given a public carousel whose cover is a site-relative image
    When its viewer page metadata is generated
    Then the Open Graph and Twitter image URLs start with "https://marinssolutions.com"

  Scenario: The sitemap pages through feeds longer than one page
    Given more published posts and public carousels than one feed page holds
    When the sitemap is generated
    Then it lists the items of every page, up to a safety cap of pages

