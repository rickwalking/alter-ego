#!/usr/bin/env python3
"""Validate rendered carousel preview slides for both supported languages."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, TypeAlias, cast

_BACKEND_SRC = Path(__file__).resolve().parents[1] / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

from rag_backend.application.services.carousel.visual_qa_expectations import (  # noqa: E402
    VisualQaExpectations,
    resolve_visual_qa_expectations,
)

PROJECT_ID_DEFAULT = "191223a4-9499-4e66-84d6-e78bdee4e695"
BASE_URL_DEFAULT = "http://127.0.0.1:8000"
EMAIL_ENV = "CAROUSEL_QA_EMAIL"
AUTH_SECRET_ENV = "CAROUSEL_QA_PASSWORD"  # noqa: S105 - environment variable name.
DEFAULT_OUTPUT_DIR_NAME = "carousel-visual-qa"
LANGUAGES = ("pt", "en")
SWIPE_TEXT = "Swipe \u2192"
FORBIDDEN_SWIPE_TEXT = "Deslize"
MIN_IMAGE_BYTES = 1024
HTTP_SCHEMES = frozenset({"http", "https"})
JPEG_HEADER_MIN_BYTES = 4
JPEG_MARKER_START_OFFSET = 2
JPEG_SEGMENT_LENGTH_BYTES = 2
JPEG_SEGMENT_LENGTH_MIN = 2
JPEG_SOI_PREFIX = b"\xff\xd8"
JPEG_MARKER_PREFIX = 0xFF
JPEG_START_OF_FRAME_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}
CONTACT_THUMB_WIDTH = 300
CONTACT_THUMB_HEIGHT = 375
CONTACT_LABEL_HEIGHT = 28
CONTACT_GAP = 18
CONTACT_COLUMNS = 4
CONTACT_BACKGROUND = "white"
CONTACT_TEXT = "black"
CONTACT_JPEG_QUALITY = 92

JsonValue: TypeAlias = (
    bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"] | None
)


class CarouselVisualQaError(RuntimeError):
    """Raised when carousel visual QA detects a failing condition."""


class PayloadShapeError(TypeError):
    """Raised when an API payload has an unexpected shape."""


@dataclass(frozen=True, kw_only=True)
class QaConfig:
    """Runtime configuration for carousel visual QA."""

    base_url: str
    project_id: str
    email: str
    password: str
    output_dir: Path
    manifest_path: Path | None
    use_hd: bool


@dataclass(frozen=True, kw_only=True)
class SlideImage:
    """Downloaded slide image metadata."""

    language: str
    number: int
    path: Path
    width: int
    height: int
    size: int


@dataclass(frozen=True, kw_only=True)
class SlideDownload:
    """Download request for one rendered slide."""

    opener: urllib.request.OpenerDirector
    config: QaConfig
    expectations: VisualQaExpectations
    language: str
    number: int
    url_path: str


@dataclass(frozen=True)
class ContactSheetSpec:
    """Contact sheet geometry derived from the number of slides."""

    rows: int
    width: int
    height: int


def _fail(message: str) -> NoReturn:
    raise CarouselVisualQaError(message)


def _fail_type(message: str) -> NoReturn:
    raise PayloadShapeError(message)


def _default_output_root() -> Path:
    return Path(tempfile.gettempdir()) / DEFAULT_OUTPUT_DIR_NAME


def _parse_args() -> QaConfig:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=BASE_URL_DEFAULT)
    parser.add_argument("--project-id", default=PROJECT_ID_DEFAULT)
    parser.add_argument("--email", default=os.getenv(EMAIL_ENV, ""))
    parser.add_argument("--password", default=os.getenv(AUTH_SECRET_ENV, ""))
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--manifest-path", default="")
    parser.add_argument(
        "--standard",
        action="store_true",
        help="Validate standard slide dimensions instead of HD preview dimensions",
    )
    args = parser.parse_args()
    if not args.email:
        parser.error(f"--email or {EMAIL_ENV} is required")
    if not args.password:
        parser.error(f"--password or {AUTH_SECRET_ENV} is required")
    output_dir = Path(args.output_dir) if args.output_dir else _default_output_root()
    manifest_path = Path(args.manifest_path) if args.manifest_path else None
    return QaConfig(
        base_url=str(args.base_url).rstrip("/"),
        project_id=str(args.project_id),
        email=str(args.email),
        password=str(args.password),
        output_dir=output_dir / str(args.project_id),
        manifest_path=manifest_path,
        use_hd=not bool(args.standard),
    )


def _assert_http_url(url: str) -> None:
    scheme = urllib.parse.urlparse(url).scheme
    if scheme not in HTTP_SCHEMES:
        _fail(f"Unsupported URL scheme for {url}")


def _request_json(
    opener: urllib.request.OpenerDirector,
    url: str,
    data: bytes | None = None,
) -> dict[str, JsonValue]:
    _assert_http_url(url)
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = urllib.request.Request(  # noqa: S310 - URL scheme is validated above.
        url,
        data=data,
        headers=headers,
        method=None,
    )
    try:
        with opener.open(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        _fail(f"HTTP {exc.code} while requesting {url}")
    except urllib.error.URLError as exc:
        _fail(f"Could not connect to {url}: {exc.reason}")
    if not isinstance(payload, dict):
        _fail_type(f"Expected JSON object from {url}")
    return cast(dict[str, JsonValue], payload)


def _authenticated_opener(config: QaConfig) -> urllib.request.OpenerDirector:
    cookies = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(cookies)
    payload = json.dumps(
        {"email": config.email, "password": config.password}
    ).encode("utf-8")
    _request_json(opener, f"{config.base_url}/api/auth/token", payload)
    return opener


def _design_preview_url(config: QaConfig, language: str) -> str:
    return (
        f"{config.base_url}/api/carousels/"
        f"{config.project_id}/preview/design/{language}"
    )


def _image_url(config: QaConfig, image_path: str) -> str:
    return urllib.parse.urljoin(f"{config.base_url}/", image_path.lstrip("/"))


def _get_dict(payload: dict[str, JsonValue], key: str) -> dict[str, JsonValue]:
    value = payload.get(key)
    if not isinstance(value, dict):
        _fail_type(f"Expected object at key {key!r}")
    return cast(dict[str, JsonValue], value)


def _get_string_list(payload: dict[str, JsonValue], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        _fail(f"Expected string list at key {key!r}")
    return cast(list[str], value)


def _workflow_state_url(config: QaConfig) -> str:
    return f"{config.base_url}/api/carousels/{config.project_id}/workflow/state"


def _load_manifest_payload(config: QaConfig) -> dict[str, JsonValue] | None:
    if config.manifest_path is not None:
        if not config.manifest_path.is_file():
            _fail(f"Manifest not found: {config.manifest_path}")
        payload = json.loads(config.manifest_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            _fail_type(f"Expected JSON object in manifest {config.manifest_path}")
        return cast(dict[str, JsonValue], payload)
    return None


def _resolve_expectations(
    opener: urllib.request.OpenerDirector,
    config: QaConfig,
) -> VisualQaExpectations:
    manifest_payload = _load_manifest_payload(config)
    workflow_payload: dict[str, JsonValue] | None = None
    try:
        workflow_payload = _request_json(opener, _workflow_state_url(config))
    except CarouselVisualQaError:
        workflow_payload = None
    return resolve_visual_qa_expectations(
        manifest_payload=(
            cast(dict[str, object], manifest_payload)
            if manifest_payload is not None
            else None
        ),
        workflow_payload=(
            cast(dict[str, object], workflow_payload)
            if workflow_payload is not None
            else None
        ),
        use_hd=config.use_hd,
    )


def _validate_design_payload(
    payload: dict[str, JsonValue],
    language: str,
    expectations: VisualQaExpectations,
) -> list[str]:
    raw = json.dumps(payload, ensure_ascii=False)
    layout = _get_dict(payload, "layout")
    swipe_text = layout.get("swipe_text")
    if swipe_text != SWIPE_TEXT:
        _fail(
            f"{language} swipe_text={swipe_text!r}, "
            f"expected {SWIPE_TEXT!r}"
        )
    if FORBIDDEN_SWIPE_TEXT in raw:
        _fail(
            f"{language} design preview still contains "
            f"{FORBIDDEN_SWIPE_TEXT!r}"
        )
    images = _get_dict(payload, "images")
    urls = _get_string_list(images, f"rendered_slides_{language}")
    if len(urls) != expectations.slide_count:
        _fail(
            f"{language} rendered slide URL count is {len(urls)}, "
            f"expected {expectations.slide_count}"
        )
    return urls


def _download_file(
    opener: urllib.request.OpenerDirector,
    url: str,
    path: Path,
) -> int:
    _assert_http_url(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with opener.open(url, timeout=30) as response:
            content = response.read()
    except urllib.error.HTTPError as exc:
        _fail(f"HTTP {exc.code} while downloading {url}")
    except urllib.error.URLError as exc:
        _fail(f"Could not download {url}: {exc.reason}")
    path.write_bytes(content)
    return len(content)


def _jpeg_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < JPEG_HEADER_MIN_BYTES or data[:2] != JPEG_SOI_PREFIX:
        _fail(f"{path} is not a JPEG")
    index = JPEG_MARKER_START_OFFSET
    while index < len(data):
        while index < len(data) and data[index] == JPEG_MARKER_PREFIX:
            index += 1
        if index >= len(data):
            break
        marker = data[index]
        index += 1
        if marker in {0xD8, 0xD9}:
            continue
        if index + JPEG_SEGMENT_LENGTH_BYTES > len(data):
            break
        segment_length = int.from_bytes(data[index : index + 2], "big")
        if segment_length < JPEG_SEGMENT_LENGTH_MIN:
            _fail(f"{path} has invalid JPEG segment length")
        if marker in JPEG_START_OF_FRAME_MARKERS:
            height = int.from_bytes(data[index + 3 : index + 5], "big")
            width = int.from_bytes(data[index + 5 : index + 7], "big")
            return width, height
        index += segment_length
    _fail(f"{path} is missing JPEG dimensions")


def _validate_dimensions(
    image: SlideImage,
    expectations: VisualQaExpectations,
) -> None:
    width_delta = abs(image.width - expectations.expected_width)
    height_delta = abs(image.height - expectations.expected_height)
    if (
        width_delta > expectations.dimension_tolerance_px
        or height_delta > expectations.dimension_tolerance_px
    ):
        _fail(
            f"{image.path} is {image.width}x{image.height}, "
            f"expected {expectations.expected_width}x{expectations.expected_height} "
            f"+/-{expectations.dimension_tolerance_px}"
        )
    if image.size < MIN_IMAGE_BYTES:
        _fail(f"{image.path} is too small: {image.size} bytes")


def _download_slide(request: SlideDownload) -> SlideImage:
    path = request.config.output_dir / request.language / f"slide_{request.number}.jpg"
    size = _download_file(
        request.opener,
        _image_url(request.config, request.url_path),
        path,
    )
    width, height = _jpeg_dimensions(path)
    image = SlideImage(
        language=request.language,
        number=request.number,
        path=path,
        width=width,
        height=height,
        size=size,
    )
    _validate_dimensions(image, request.expectations)
    return image


def _contact_sheet_spec(image_count: int) -> ContactSheetSpec:
    rows = math.ceil(image_count / CONTACT_COLUMNS)
    return ContactSheetSpec(
        rows=rows,
        width=CONTACT_COLUMNS * CONTACT_THUMB_WIDTH
        + (CONTACT_COLUMNS + 1) * CONTACT_GAP,
        height=rows * (CONTACT_THUMB_HEIGHT + CONTACT_LABEL_HEIGHT)
        + (rows + 1) * CONTACT_GAP,
    )


def _contact_position(index: int) -> tuple[int, int]:
    col = index % CONTACT_COLUMNS
    row = index // CONTACT_COLUMNS
    return (
        CONTACT_GAP + col * (CONTACT_THUMB_WIDTH + CONTACT_GAP),
        CONTACT_GAP
        + row * (CONTACT_THUMB_HEIGHT + CONTACT_LABEL_HEIGHT + CONTACT_GAP),
    )


def _write_contact_sheet(images: list[SlideImage], output_path: Path) -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        _fail("Pillow is required to write contact sheets")
    spec = _contact_sheet_spec(len(images))
    sheet = Image.new("RGB", (spec.width, spec.height), CONTACT_BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    for idx, image in enumerate(images):
        x, y = _contact_position(idx)
        with Image.open(image.path) as slide:
            slide.thumbnail((CONTACT_THUMB_WIDTH, CONTACT_THUMB_HEIGHT))
            sheet.paste(slide.convert("RGB"), (x, y))
        label = f"{image.language} slide {image.number}"
        draw.text((x, y + CONTACT_THUMB_HEIGHT + 6), label, fill=CONTACT_TEXT)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, "JPEG", quality=CONTACT_JPEG_QUALITY)


def _run(config: QaConfig) -> tuple[list[SlideImage], VisualQaExpectations]:
    opener = _authenticated_opener(config)
    expectations = _resolve_expectations(opener, config)
    all_images: list[SlideImage] = []
    for language in LANGUAGES:
        payload = _request_json(opener, _design_preview_url(config, language))
        urls = _validate_design_payload(payload, language, expectations)
        language_images = [
            _download_slide(
                SlideDownload(
                    opener=opener,
                    config=config,
                    expectations=expectations,
                    language=language,
                    number=index,
                    url_path=url,
                )
            )
            for index, url in enumerate(urls, start=1)
        ]
        _write_contact_sheet(
            language_images,
            config.output_dir / f"{language}-contact.jpg",
        )
        all_images.extend(language_images)
    return all_images, expectations


def main() -> int:
    config = _parse_args()
    try:
        images, expectations = _run(config)
    except (CarouselVisualQaError, PayloadShapeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "PASS: validated "
        f"{len(images)} rendered slides "
        f"(source={expectations.source}, "
        f"slides={expectations.slide_count}, "
        f"dimensions={expectations.expected_width}x{expectations.expected_height}, "
        f"artifact_version={expectations.artifact_version or 'legacy'})"
    )
    print(f"Output: {config.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
