Feature: PDF slide builder for LinkedIn document posting
  As a carousel author
  I want the exported slides assembled into a single PDF
  So I can upload it as a LinkedIn document post

  Scenario: N slides produce a PDF with N pages
    Given 6 exported 1080x1350 JPG slides
    When the PdfSlideBuilder.build is called
    Then a file carousel.pdf is written to the output directory
    And the PDF has 6 pages

  Scenario: Page dimensions match the source image dimensions
    Given a single 1080x1350 JPG slide
    When the PdfSlideBuilder.build is called
    Then the PDF page size corresponds to 1080x1350 in PDF points

  Scenario: Empty slide list raises a clear error
    Given an empty slide_paths list
    When the PdfSlideBuilder.build is called
    Then a ValueError is raised mentioning "empty"

  Scenario: Missing slide file raises FileNotFoundError
    Given a slide_paths list referencing a non-existent file
    When the PdfSlideBuilder.build is called
    Then FileNotFoundError is raised

  Scenario: Builder returns the absolute path of the written PDF
    Given valid slide files
    When the PdfSlideBuilder.build is called
    Then the returned string ends with "carousel.pdf"
    And the file exists at that path
