"""Classifies files by extension and magic bytes."""

from __future__ import annotations

from ..core.entities import Category, FileEntry

# Extension-based classification
_EXT_MAP: dict[str, Category] = {
    # Documents
    ".pdf": Category.DOCUMENTS,
    ".doc": Category.DOCUMENTS,
    ".docx": Category.DOCUMENTS,
    ".txt": Category.DOCUMENTS,
    ".odt": Category.DOCUMENTS,
    ".rtf": Category.DOCUMENTS,
    ".xls": Category.DOCUMENTS,
    ".xlsx": Category.DOCUMENTS,
    ".ppt": Category.DOCUMENTS,
    ".pptx": Category.DOCUMENTS,
    ".csv": Category.DOCUMENTS,
    ".md": Category.DOCUMENTS,
    # Photos
    ".jpg": Category.PHOTOS,
    ".jpeg": Category.PHOTOS,
    ".png": Category.PHOTOS,
    ".gif": Category.PHOTOS,
    ".bmp": Category.PHOTOS,
    ".webp": Category.PHOTOS,
    ".tiff": Category.PHOTOS,
    ".tif": Category.PHOTOS,
    ".heic": Category.PHOTOS,
    ".heif": Category.PHOTOS,
    ".raw": Category.PHOTOS,
    ".cr2": Category.PHOTOS,
    ".nef": Category.PHOTOS,
    # Videos
    ".mp4": Category.VIDEOS,
    ".avi": Category.VIDEOS,
    ".mkv": Category.VIDEOS,
    ".mov": Category.VIDEOS,
    ".wmv": Category.VIDEOS,
    ".flv": Category.VIDEOS,
    ".webm": Category.VIDEOS,
    ".m4v": Category.VIDEOS,
    # Music
    ".mp3": Category.MUSIC,
    ".flac": Category.MUSIC,
    ".wav": Category.MUSIC,
    ".ogg": Category.MUSIC,
    ".aac": Category.MUSIC,
    ".m4a": Category.MUSIC,
    ".wma": Category.MUSIC,
    # Archives
    ".zip": Category.ARCHIVES,
    ".tar": Category.ARCHIVES,
    ".gz": Category.ARCHIVES,
    ".tgz": Category.ARCHIVES,
    ".bz2": Category.ARCHIVES,
    ".7z": Category.ARCHIVES,
    ".rar": Category.ARCHIVES,
    ".xz": Category.ARCHIVES,
}

# Never-extract extensions
_NEVER_EXTRACT: set[str] = {".iso", ".exe", ".dmg", ".deb", ".img", ".bin"}


def classify_by_extension(file_entry: FileEntry) -> Category:
    """Classify a file based on its extension."""
    ext = file_entry.extension
    if ext in _NEVER_EXTRACT:
        file_entry.is_archive = False
        return Category.OTHERS
    return _EXT_MAP.get(ext, Category.OTHERS)


def classify_by_magic(file_entry: FileEntry, magic_bytes: bytes | None) -> Category | None:
    """Attempt to classify by magic bytes. Returns None if inconclusive."""
    if not magic_bytes or len(magic_bytes) < 4:
        return None

    # JPEG
    if magic_bytes[:3] == b"\xff\xd8\xff":
        return Category.PHOTOS
    # PNG
    if magic_bytes[:4] == b"\x89PNG":
        return Category.PHOTOS
    # GIF
    if magic_bytes[:4] == b"GIF8":
        return Category.PHOTOS
    # PDF
    if magic_bytes[:5] == b"%PDF-":
        return Category.DOCUMENTS
    # ZIP
    if magic_bytes[:2] == b"PK":
        return Category.ARCHIVES
    # GZIP
    if magic_bytes[:2] == b"\x1f\x8b":
        return Category.ARCHIVES
    # RAR
    if magic_bytes[:4] in (b"Rar!", b"\x52\x61\x72\x21"):
        return Category.ARCHIVES

    return None


def detect_corruption(file_entry: FileEntry, magic_bytes: bytes | None) -> str | None:
    """Return a reason string if the file appears corrupted, else None."""
    if file_entry.size_bytes == 0:
        return "zero-size file"

    ext = file_entry.extension
    if ext in (".jpg", ".jpeg") and magic_bytes and magic_bytes[:3] != b"\xff\xd8\xff":
        return "invalid JPEG signature"
    if ext == ".png" and magic_bytes and magic_bytes[:4] != b"\x89PNG":
        return "invalid PNG signature"
    if ext == ".pdf" and magic_bytes and magic_bytes[:5] != b"%PDF-":
        return "invalid PDF signature"
    if ext in (".zip",) and magic_bytes and magic_bytes[:2] != b"PK":
        return "invalid ZIP signature"

    return None


def classify_file(file_entry: FileEntry, magic_bytes: bytes | None = None) -> FileEntry:
    """Full classification: magic bytes override extension, then detect corruption."""
    corruption_reason = detect_corruption(file_entry, magic_bytes)
    if corruption_reason:
        file_entry.category = Category.CORRUPTED
        file_entry.status = file_entry.status  # preserve existing status
        file_entry.corruption_reason = corruption_reason
        return file_entry

    category = classify_by_magic(file_entry, magic_bytes)
    if category is None:
        category = classify_by_extension(file_entry)

    file_entry.category = category

    if category == Category.ARCHIVES and file_entry.extension not in _NEVER_EXTRACT:
        file_entry.is_archive = True

    return file_entry
