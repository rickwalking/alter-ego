Feature: The Langfuse object store image stays pullable and immutable (AE-0480)
  MinIO, Inc. withdrew its public images: Docker Hub minio/minio first
  (AE-0331), then quay.io/minio/minio (401 since 2026-10-13). A fresh pull of a
  withdrawn image breaks Langfuse on a new droplet or after the deploy prunes
  cached images, so the production object store must come from a maintained
  registry and be pinned by digest.

  Scenario: The MinIO services are pinned by tag and sha256 digest
    Given the production compose file
    When the minio and minio-init image references are read
    Then each one carries a release tag and a sha256 digest
    And both services use the same reference

  Scenario: The MinIO services never reference a withdrawn registry
    Given the production compose file
    When the minio and minio-init image references are read
    Then none of them comes from quay.io/minio or Docker Hub minio/minio

  Scenario: The object store keeps its data volume and credentials
    Given the production compose file
    When the minio service is read
    Then it serves /data from the minio_data volume as the langfuse root user
