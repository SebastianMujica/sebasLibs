"""Pytest fixtures with temporary files for testing."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir():
    """Create a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_files(tmp_dir: Path) -> list[Path]:
    """Create a set of sample files for testing."""
    # Documents
    (tmp_dir / "report.pdf").write_bytes(b"%PDF-1.4 fake content")
    (tmp_dir / "notes.txt").write_text("Hello world")

    # Photos
    (tmp_dir / "photo.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    (tmp_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    # Archives
    (tmp_dir / "backup.zip").write_bytes(b"PK\x03\x04" + b"\x00" * 100)

    # Corrupted (zero-size)
    (tmp_dir / "empty.jpg").touch()

    # Others
    (tmp_dir / "unknown.xyz").write_text("unknown format")

    return [(tmp_dir / f) for f in tmp_dir.iterdir() if f.is_file()]


@pytest.fixture
def empty_dir(tmp_dir: Path) -> Path:
    """An empty temporary directory."""
    return tmp_dir
