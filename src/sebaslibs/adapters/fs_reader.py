"""File reader adapter: directory scanning, metadata, magic bytes."""

from __future__ import annotations

import os
from pathlib import Path

from ..core.ports import FileReaderPort

MAGIC_BYTES_SIZE = 32


class FileSystemReader(FileReaderPort):
    def scan_directory(self, path: Path) -> list[Path]:
        files: list[Path] = []
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file(follow_symlinks=False):
                    files.append(Path(entry.path))
        return files

    def read_metadata(self, file_path: Path) -> dict:
        stat = file_path.stat()
        return {
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "ctime": stat.st_ctime,
        }

    def read_magic_bytes(self, file_path: Path) -> bytes | None:
        try:
            with open(file_path, "rb") as f:
                return f.read(MAGIC_BYTES_SIZE)
        except (OSError, PermissionError):
            return None
