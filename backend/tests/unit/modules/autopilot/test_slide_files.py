"""PT slide paths stay on disk (AE-0355)."""

from __future__ import annotations

from pathlib import Path

from rag_backend.modules.autopilot.infrastructure.slide_files import pt_slide_paths


def test_standard_pt_directory_is_capped_at_ten(tmp_path: Path) -> None:
    language = tmp_path / "pt"
    language.mkdir()
    for number in range(1, 13):
        (language / f"slide_{number}.jpg").write_bytes(b"jpeg")
    (language / "notes.txt").write_text("nope", encoding="utf-8")
    paths = pt_slide_paths(str(tmp_path))
    assert len(paths) == 10
    assert paths[0].endswith("slide_1.jpg")
    assert paths[-1].endswith("slide_10.jpg")


def test_hd_directory_is_used_when_standard_is_empty(tmp_path: Path) -> None:
    hd = tmp_path / "pt" / "hd"
    hd.mkdir(parents=True)
    (hd / "slide_2.jpg").write_bytes(b"jpeg")
    (hd / "slide_1.jpg").write_bytes(b"jpeg")
    paths = pt_slide_paths(str(tmp_path))
    assert [Path(path).name for path in paths] == ["slide_1.jpg", "slide_2.jpg"]


def test_missing_output_dir_is_empty() -> None:
    assert pt_slide_paths(None) == ()
    assert pt_slide_paths("") == ()


def test_missing_language_directory_and_non_numeric_names(tmp_path: Path) -> None:
    assert pt_slide_paths(str(tmp_path)) == ()
    language = tmp_path / "pt"
    language.mkdir()
    (language / "slide_x.jpg").write_bytes(b"jpeg")
    (language / "slide_.jpg").write_bytes(b"jpeg")
    assert pt_slide_paths(str(tmp_path)) == ()
