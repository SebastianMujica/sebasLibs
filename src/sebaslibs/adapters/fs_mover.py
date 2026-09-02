"""File mover adapter."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..core.ports import FileMoverPort


class FileSystemMover(FileMoverPort):
    def move(self, source: Path, destination: Path) -> bool:
        if not source.exists():
            return False
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            source.rename(destination)
        except OSError:
            shutil.move(str(source), str(destination))
        return destination.exists()

    def safe_move(self, source: Path, destination: Path) -> Path:
        if not destination.exists():
            return destination

        stem = destination.stem
        suffix = destination.suffix
        counter = 1
        while True:
            new_name = f"{stem} ({counter}){suffix}"
            new_dest = destination.parent / new_name
            if not new_dest.exists():
                return new_dest
            counter += 1
