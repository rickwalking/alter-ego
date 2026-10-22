"""Production MinIO image pin for the Langfuse stack.

Feature: backend/tests/features/compose_object_storage_image_ae0480.feature
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
COMPOSE = REPO_ROOT / "docker-compose.prod.yml"
OBJECT_STORE_SERVICES = ("minio", "minio-init")
PINNED = re.compile(r"^[a-z0-9.\-/]+:[A-Za-z0-9._\-]+@sha256:[0-9a-f]{64}$")
WITHDRAWN = (
    re.compile(r"^quay\.io/minio/"),
    re.compile(r"^(docker\.io/)?minio/minio[:@]"),
    re.compile(r"^(docker\.io/)?minio/mc[:@]"),
)


def _service(name: str) -> dict[str, object]:
    document = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    service = document["services"][name]
    assert isinstance(service, dict), f"{name} is not a compose service mapping"
    return service


def _images() -> dict[str, str]:
    return {name: str(_service(name)["image"]) for name in OBJECT_STORE_SERVICES}


# Scenario: The MinIO services are pinned by tag and sha256 digest
def test_object_store_images_are_pinned_by_tag_and_digest() -> None:
    images = _images()
    for name, image in images.items():
        assert PINNED.match(image), f"{name} is not pinned by tag@sha256: {image}"
    assert len(set(images.values())) == 1


# Scenario: The MinIO services never reference a withdrawn registry
def test_object_store_images_avoid_withdrawn_registries() -> None:
    for name, image in _images().items():
        hits = [pattern.pattern for pattern in WITHDRAWN if pattern.search(image)]
        assert not hits, f"{name} uses a withdrawn MinIO image: {image}"


# Scenario: The object store keeps its data volume and credentials
def test_object_store_keeps_data_volume_and_credentials() -> None:
    minio = _service("minio")
    volumes = minio["volumes"]
    environment = minio["environment"]
    assert isinstance(volumes, list)
    assert isinstance(environment, dict)
    assert minio["command"] == "server /data"
    assert "minio_data:/data" in volumes
    assert environment["MINIO_ROOT_USER"] == "langfuse"
    assert environment["MINIO_ROOT_PASSWORD"] == "${LANGFUSE_MINIO_PASSWORD:-changeme}"
