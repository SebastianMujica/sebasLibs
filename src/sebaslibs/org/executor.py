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
        trash_dir: Path | None = None,
        hard_delete: bool = False,
    ) -> None:
        self.plan = plan
        self.mover = mover or DefaultMover()
        self.simulate = simulate
        self.resume = resume
        self.trash_dir = trash_dir or plan.destination / "Trash"
        self.hard_delete = hard_delete

    def run(self) -> list[FileEntry]:
        """Execute the plan, moving files and updating status."""
        results: list[FileEntry] = []
        entries = self.plan.entries

        if self.resume:
            entries = [e for e in entries if e.status == FileStatus.PENDING]

        for entry in entries:
            if entry.status == FileStatus.MOVED:
                continue

            # Handle skip action from rules
            if entry.metadata.get("action") == "skip":
                entry.status = FileStatus.PENDING
                results.append(entry)
                continue

            # Handle delete action from rules
            if entry.metadata.get("action") == "delete":
                if not self.simulate:
                    self._delete_file(entry)
                results.append(entry)
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

    def _delete_file(self, entry: FileEntry) -> None:
        """Delete or move to trash based on hard_delete flag."""
        if not entry.source_path.exists():
            entry.status = FileStatus.ERROR
            return

        if self.hard_delete:
            try:
                entry.source_path.unlink()
                entry.status = FileStatus.MOVED
                entry.metadata["deleted"] = "hard"
            except OSError:
                entry.status = FileStatus.ERROR
        else:
            # Reversible delete: move to Trash/
            trash_dest = self.trash_dir / entry.original_name
            try:
                safe_trash = self.mover.safe_move(entry.source_path, trash_dest)
                self.mover.move(entry.source_path, safe_trash)
                entry.status = FileStatus.MOVED
                entry.destination_path = safe_trash
                entry.metadata["deleted"] = "trash"
                entry.metadata["trash_path"] = str(safe_trash)
            except Exception:
                entry.status = FileStatus.ERROR


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
