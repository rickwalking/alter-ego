@AE-0494 @backend @carousel
Feature: The owner deletes a photo from the private photo library
  As the owner of a personal photo library
  I want to delete photos I no longer want on the server
  So that my personal data is gone, unless a carousel still needs the photo

  Scenario: An unused photo is deleted with its file
    Given the owner uploaded a photo that no carousel uses
    When the owner deletes the photo
    Then the response is 204
    And the photo is no longer listed and its image returns 404
    And its stored file is removed

  Scenario: A file shared by another owner's row is kept
    Given two owners uploaded the same photo bytes
    When one owner deletes the photo
    Then the other owner's photo still serves its image

  Scenario: A photo used by a carousel cannot be deleted
    Given a carousel uses the owner's photo as its slide-1 photo
    When the owner deletes the photo
    Then the response is 409 with the carousel id and title
    And the photo is still listed

  Scenario: A photo used as a slide-1 cover or creator asset cannot be deleted
    Given a carousel uses the owner's photo as its slide-1 cover or its creator asset
    When the owner deletes the photo
    Then the response is 409 with that carousel

  Scenario: Another user cannot delete the photo
    Given another user or an admin who is not the owner
    When they delete the owner's photo
    Then the response is 404, as for an unknown photo, and the photo is kept

  Scenario: Deleting an unknown photo returns not found
    When the owner deletes a photo id that does not exist
    Then the response is 404

  Scenario: A photo an autopilot topic uses as its cover cannot be deleted
    Given a GrokBot cover row points at the owner's photo, claimed by a pending topic or not yet claimed
    When the owner deletes the photo
    Then the response is 409 listing those topics
    And the photo and its file are kept

  Scenario: A GrokBot cover is not deleted from the photo library
    Given the owner's asset is a GrokBot slide-1 cover
    When the owner deletes it from the photo library
    Then the response is 409 "creator_asset_cover_managed" and nothing is deleted

  Scenario: A stored file that cannot be removed is logged, not an error
    Given the owner's unused photo whose file the server cannot remove
    When the owner deletes the photo
    Then the response is 204 and the photo is no longer listed
    And a warning with the photo id is logged

  Scenario: A carousel that starts using the photo during a delete keeps it
    Given the owner deletes a photo
    Then the photo row is locked before the in-use check
    So a carousel that starts using the photo meanwhile waits for the delete and never loses its photo silently
