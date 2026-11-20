Feature: A Reel is the account's own under either of its Graph ids (AE-0632)
  Instagram answers the configured account id (META_IG_USER_ID) with a second id
  for the same account, and names that second id as a media's owner. The repost
  draft must accept a Reel owned under either id and still refuse anyone else's.

  Scenario: A Reel Graph attributes to the account's other id is the account's own
    Given META_IG_USER_ID is the configured account id
    And Graph reports the account as another id, and names that id as the Reel's owner
    When the scout asks for that Reel
    Then the Reel is found and the account id is looked up once

  Scenario: A Reel owned by anyone else is still not found
    Given Graph names a different account, or no owner, for the media
    When the scout asks for that Reel
    Then it is not found
