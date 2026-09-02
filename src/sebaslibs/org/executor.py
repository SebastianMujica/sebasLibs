"""Executor: moves files according to a plan, with checkpoint and resume support."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..core.entities import FileEntry, FileStatus, Plan
from ..core.ports import FileMoverPort


class Executor:
    def __init__(
        self,
        plan: Plan,
        mover: FileMoverPort | None = None,
        simulate: bool = False,
        resume: bool = False,
    ) -> None:
        self.plan = plan
        self.mover = mover or DefaultMover()
        self.simulate = simulate
        self.resume = resume

    def run(self) -> list[FileEntry]:
        """Execute the plan, moving files and updating status."""
        results: list[FileEntry] = []
        entries = self.plan.entries

        if self.resume:
            entries = [e for e in entries if e.status == FileStatus.PENDING]

        for entry in entries:
            if entry.status == FileStatus.MOVED:
                continue

            entry.status = FileStatus.PROCESSING

            if self.simulate:
                entry.status = FileStatus.PENDING
                results.append(entry)
                continue

            dest = entry.destination_path
            if not dest:
                entry.status = FileStatus.ERROR
                results.append(entry)
                continue

            # Handle name collisions
            safe_dest = self.mover.safe_move(entry.source_path, dest)

            try:
                success = self.mover.move(entry.source_path, safe_dest)
                if success:
                    entry.status = FileStatus.MOVED
                    entry.destination_path = safe_dest
                else:
                    entry.status = FileStatus.ERROR
            except Exception:
                entry.status = FileStatus.ERROR

            results.append(entry)

        return results


class DefaultMover(FileMoverPort):
    """Default mover using os.rename (same volume) or shutil.move (cross-volume)."""

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
