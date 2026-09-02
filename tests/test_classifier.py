"""Tests for the organizer classifier."""

from pathlib import Path

from sebaslibs.core.entities import Category, FileEntry
from sebaslibs.org.classifier import classify_file, detect_corruption


class TestClassifier:
    def test_classify_pdf_by_magic(self):
        entry = FileEntry(
            original_name="report.pdf",
            source_path=Path("/tmp/report.pdf"),
            size_bytes=100,
        )
        magic = b"%PDF-1.4 fake content"
        result = classify_file(entry, magic)
        assert result.category == Category.DOCUMENTS

    def test_classify_jpeg_by_magic(self):
        entry = FileEntry(
            original_name="photo.jpg",
            source_path=Path("/tmp/photo.jpg"),
            size_bytes=100,
        )
        magic = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        result = classify_file(entry, magic)
        assert result.category == Category.PHOTOS

    def test_classify_png_by_magic(self):
        entry = FileEntry(
            original_name="image.png",
            source_path=Path("/tmp/image.png"),
            size_bytes=100,
        )
        magic = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        result = classify_file(entry, magic)
        assert result.category == Category.PHOTOS

    def test_classify_by_extension_fallback(self):
        entry = FileEntry(
            original_name="song.mp3",
            source_path=Path("/tmp/song.mp3"),
            size_bytes=100,
        )
        result = classify_file(entry, None)
        assert result.category == Category.MUSIC

    def test_corrupted_zero_size(self):
        entry = FileEntry(
            original_name="empty.jpg",
            source_path=Path("/tmp/empty.jpg"),
            size_bytes=0,
        )
        result = classify_file(entry, None)
        assert result.category == Category.CORRUPTED
        assert result.corruption_reason == "zero-size file"

    def test_corrupted_invalid_signature(self):
        entry = FileEntry(
            original_name="fake.jpg",
            source_path=Path("/tmp/fake.jpg"),
            size_bytes=100,
        )
        magic = b"not a jpeg file at all"
        result = classify_file(entry, magic)
        assert result.category == Category.CORRUPTED
        assert "invalid JPEG" in result.corruption_reason

    def test_classify_archive(self):
        entry = FileEntry(
            original_name="backup.zip",
            source_path=Path("/tmp/backup.zip"),
            size_bytes=200,
        )
        magic = b"PK\x03\x04" + b"\x00" * 100
        result = classify_file(entry, magic)
        assert result.category == Category.ARCHIVES
        assert result.is_archive is True

    def test_unknown_extension(self):
        entry = FileEntry(
            original_name="weird.xyz",
            source_path=Path("/tmp/weird.xyz"),
            size_bytes=50,
        )
        result = classify_file(entry, None)
        assert result.category == Category.OTHERS


class TestDetectCorruption:
    def test_zero_size(self):
        entry = FileEntry(
            original_name="empty.jpg",
            source_path=Path("/tmp/empty.jpg"),
            size_bytes=0,
        )
        assert detect_corruption(entry, None) == "zero-size file"

    def test_valid_jpeg(self):
        entry = FileEntry(
            original_name="photo.jpg",
            source_path=Path("/tmp/photo.jpg"),
            size_bytes=100,
        )
        magic = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        assert detect_corruption(entry, magic) is None

    def test_invalid_jpeg(self):
        entry = FileEntry(
            original_name="fake.jpg",
            source_path=Path("/tmp/fake.jpg"),
            size_bytes=100,
        )
        magic = b"not a jpeg"
        assert detect_corruption(entry, magic) is not None
