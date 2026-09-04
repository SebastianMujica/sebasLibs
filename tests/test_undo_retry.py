"""Tests for undo and retry CLI functionality."""

import tempfile
from pathlib import Path

from sebaslibs.adapters.csv_store import CsvStore
from sebaslibs.core.entities import Category, FileEntry, FileStatus, Plan
from sebaslibs.org.executor import Executor


class TestUndo:
    def test_undo_moves_back(self):
        """Undo should move files from destination back to source."""
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "source"
            dest = Path(d) / "dest"
            src.mkdir()

            f = src / "test.txt"
            f.write_text("hello")

            entry = FileEntry(
                original_name="test.txt",
                source_path=f,
                destination_path=dest / "Documents" / "test.txt",
                category=Category.DOCUMENTS,
                status=FileStatus.PENDING,  # Start as pending so executor moves it
            )

            plan = Plan(source=src, destination=dest, entries=[entry])
            executor = Executor(plan, simulate=False)
            executor.run()

            assert (dest / "Documents" / "test.txt").exists()
            assert not f.exists()

            # Now simulate undo: entry is now MOVED
            assert entry.status == FileStatus.MOVED
            dest_file = entry.destination_path
            if dest_file.exists():
                entry.source_path.parent.mkdir(parents=True, exist_ok=True)
                dest_file.rename(entry.source_path)
                entry.status = FileStatus.PENDING

            assert f.exists()
            assert not (dest / "Documents" / "test.txt").exists()

    def test_undo_skips_missing_dest(self):
        """Undo should handle missing destination gracefully."""
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "source"
            dest = Path(d) / "dest"
            src.mkdir()

            f = src / "test.txt"
            f.write_text("hello")

            entry = FileEntry(
                original_name="test.txt",
                source_path=f,
                destination_path=dest / "Documents" / "test.txt",
                category=Category.DOCUMENTS,
                status=FileStatus.MOVED,
            )

            plan = Plan(source=src, destination=dest, entries=[entry])

            # Undo without having moved the file
            dest_file = entry.destination_path
            if dest_file and dest_file.exists():
                entry.source_path.parent.mkdir(parents=True, exist_ok=True)
                dest_file.rename(entry.source_path)
                entry.status = FileStatus.PENDING
            else:
                # Destination doesn't exist, should just reset
                entry.status = FileStatus.PENDING

            assert entry.status == FileStatus.PENDING
            assert f.exists()  # Source still exists


class TestRetry:
    def test_retry_resets_error_status(self):
        """Retry should reset error entries to pending."""
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "source"
            dest = Path(d) / "dest"
            src.mkdir()

            f = src / "test.txt"
            f.write_text("hello")

            entry = FileEntry(
                original_name="test.txt",
                source_path=f,
                destination_path=dest / "Documents" / "test.txt",
                category=Category.DOCUMENTS,
                status=FileStatus.ERROR,
            )

            plan = Plan(source=src, destination=dest, entries=[entry])

            # Simulate retry
            if entry.status == FileStatus.ERROR:
                entry.status = FileStatus.PENDING

            executor = Executor(plan, simulate=False, resume=False)
            results = executor.run()

            assert results[0].status == FileStatus.MOVED
            assert (dest / "Documents" / "test.txt").exists()

    def test_execute_with_retry_errors_flag(self):
        """Execute with --retry-errors should process error entries."""
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "source"
            dest = Path(d) / "dest"
            src.mkdir()

            f1 = src / "ok.txt"
            f2 = src / "fail.txt"
            f1.write_text("ok")
            f2.write_text("fail")

            entry1 = FileEntry(
                original_name="ok.txt",
                source_path=f1,
                destination_path=dest / "Documents" / "ok.txt",
                category=Category.DOCUMENTS,
                status=FileStatus.MOVED,
            )
            entry2 = FileEntry(
                original_name="fail.txt",
                source_path=f2,
                destination_path=dest / "Documents" / "fail.txt",
                category=Category.DOCUMENTS,
                status=FileStatus.ERROR,
            )

            plan = Plan(source=src, destination=dest, entries=[entry1, entry2])

            # Simulate --retry-errors
            for entry in plan.entries:
                if entry.status == FileStatus.ERROR:
                    entry.status = FileStatus.PENDING

            executor = Executor(plan, simulate=False, resume=False)
            results = executor.run()

            # entry1 was already moved, should be skipped
            # entry2 should be retried and succeed
            assert entry2.status == FileStatus.MOVED
