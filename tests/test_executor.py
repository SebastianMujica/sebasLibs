"""Tests for the organizer executor."""

from pathlib import Path

from sebaslibs.core.entities import Category, FileEntry, FileStatus, Plan
from sebaslibs.org.executor import DefaultMover, Executor


class TestExecutor:
    def test_simulate_does_not_move(self, tmp_dir):
        source = tmp_dir / "source"
        dest = tmp_dir / "dest"
        source.mkdir()
        file_path = source / "test.txt"
        file_path.write_text("hello")

        entry = FileEntry(
            original_name="test.txt",
            source_path=file_path,
            destination_path=dest / "Documents" / "test.txt",
            category=Category.DOCUMENTS,
            status=FileStatus.PENDING,
        )
        plan = Plan(source=source, destination=dest, entries=[entry])

        executor = Executor(plan, simulate=True)
        results = executor.run()

        assert file_path.exists()
        assert results[0].status == FileStatus.PENDING

    def test_execute_moves_file(self, tmp_dir):
        source = tmp_dir / "source"
        dest = tmp_dir / "dest"
        source.mkdir()
        file_path = source / "test.txt"
        file_path.write_text("hello")

        entry = FileEntry(
            original_name="test.txt",
            source_path=file_path,
            destination_path=dest / "Documents" / "test.txt",
            category=Category.DOCUMENTS,
            status=FileStatus.PENDING,
        )
        plan = Plan(source=source, destination=dest, entries=[entry])

        executor = Executor(plan, simulate=False)
        results = executor.run()

        assert results[0].status == FileStatus.MOVED
        assert (dest / "Documents" / "test.txt").exists()

    def test_safe_move_handles_collision(self, tmp_dir):
        dest = tmp_dir / "dest"
        dest.mkdir()
        existing = dest / "photo.jpg"
        existing.write_bytes(b"\x00")

        mover = DefaultMover()
        new_path = mover.safe_move(Path("/dummy/source.jpg"), existing)

        assert new_path.name == "photo (1).jpg"
