"""Ports (interfaces) for dependency injection."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .entities import Plan


class FileReaderPort(ABC):
    @abstractmethod
    def scan_directory(self, path: Path) -> list[Path]:
        ...

    @abstractmethod
    def read_metadata(self, file_path: Path) -> dict:
        ...

    @abstractmethod
    def read_magic_bytes(self, file_path: Path) -> bytes | None:
        ...


class FileMoverPort(ABC):
    @abstractmethod
    def move(self, source: Path, destination: Path) -> bool:
        ...

    @abstractmethod
    def safe_move(self, source: Path, destination: Path) -> Path:
        """Move handling name collisions by appending a numeric suffix."""
        ...


class ArchiveReaderPort(ABC):
    @abstractmethod
    def is_archive(self, file_path: Path) -> bool:
        ...

    @abstractmethod
    def has_password(self, file_path: Path) -> bool:
        ...

    @abstractmethod
    def extract(self, archive_path: Path, dest_dir: Path, max_size_bytes: int | None = None) -> list[Path]:
        ...


class MetadataExtractorPort(ABC):
    @abstractmethod
    def extract_exif(self, file_path: Path) -> dict:
        ...


class PlanStorePort(ABC):
    @abstractmethod
    def save_plan(self, plan: Plan, output_dir: Path) -> None:
        ...

    @abstractmethod
    def load_plan(self, output_dir: Path) -> Plan | None:
        ...

    @abstractmethod
    def save_checkpoint(self, plan: Plan, output_dir: Path) -> None:
        ...

    @abstractmethod
    def load_checkpoint(self, output_dir: Path) -> Plan | None:
        ...
