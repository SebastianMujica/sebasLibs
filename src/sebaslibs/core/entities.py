"""Core domain entities shared across all tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class Category(str, Enum):
    DOCUMENTS = "Documents"
    PHOTOS = "Photos"
    VIDEOS = "Videos"
    MUSIC = "Music"
    ARCHIVES = "Archives"
    OTHERS = "Others"
    CORRUPTED = "Corrupted"


class FileStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    MOVED = "moved"
    CORRUPTED = "corrupted"
    ERROR = "error"
    ENCRYPTED = "encrypted"
    EXTRACTED = "extracted"


@dataclass
class FileEntry:
    """Represents a single file discovered during scanning."""

    original_name: str
    source_path: Path
    destination_path: Path | None = None
    category: Category | None = None
    subfolder: str | None = None
    size_bytes: int = 0
    modified: datetime | None = None
    created: datetime | None = None
    date_taken: datetime | None = None
    camera: str | None = None
    resolution: str | None = None
    status: FileStatus = FileStatus.PENDING
    corruption_reason: str | None = None
    is_archive: bool = False
    has_password: bool = False
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def extension(self) -> str:
        return self.source_path.suffix.lower()

    def effective_destination(self) -> Path:
        if self.destination_path:
            return self.destination_path
        parts: list[str] = []
        if self.category:
            parts.append(self.category.value)
        if self.subfolder:
            parts.append(self.subfolder)
        parts.append(self.original_name)
        return Path(*parts)


@dataclass
class Plan:
    """Collection of FileEntry objects representing an organization plan."""

    source: Path
    destination: Path
    entries: list[FileEntry] = field(default_factory=list)
    max_per_folder: int = 500

    @property
    def pending_count(self) -> int:
        return sum(1 for e in self.entries if e.status == FileStatus.PENDING)

    @property
    def total_count(self) -> int:
        return len(self.entries)
