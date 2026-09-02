"""Integration test: plan -> execute end-to-end."""

import tempfile
from pathlib import Path

from sebaslibs.adapters.csv_store import CsvStore
from sebaslibs.core.entities import Category, FileEntry, FileStatus, Plan
from sebaslibs.org.executor import Executor
from sebaslibs.org.planner import Planner


class TestIntegration:
    def test_plan_and_execute(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "source"
            src.mkdir()

            # Create sample files
            (src / "report.pdf").write_bytes(b"%PDF-1.4 fake content")
            (src / "photo.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
            (src / "song.mp3").write_bytes(b"fake mp3 data")

            dest = Path(d) / "dest"
            plan_dir = dest / "_organizer"

            # Phase 1: Plan
            planner = Planner(source=src, destination=dest)
            plan = planner.scan()
            assert plan.total_count == 3

            store = CsvStore()
            store.save_plan(plan, plan_dir)

            # Phase 2: Load plan and execute
            loaded_plan = store.load_plan(plan_dir)
            assert loaded_plan is not None
            assert loaded_plan.total_count == 3

            executor = Executor(loaded_plan, simulate=False)
            results = executor.run()

            moved = sum(1 for r in results if r.status == FileStatus.MOVED)
            assert moved == 3

            # Verify files exist at destinations
            for entry in loaded_plan.entries:
                assert entry.destination_path is not None
                assert entry.destination_path.exists()

    def test_plan_and_simulate(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "source"
            src.mkdir()

            (src / "test.txt").write_text("hello")

            dest = Path(d) / "dest"
            plan_dir = dest / "_organizer"

            planner = Planner(source=src, destination=dest)
            plan = planner.scan()

            store = CsvStore()
            store.save_plan(plan, plan_dir)

            loaded_plan = store.load_plan(plan_dir)
            executor = Executor(loaded_plan, simulate=True)
            results = executor.run()

            # Original file should still exist
            assert (src / "test.txt").exists()

            # Status should remain pending
            assert results[0].status == FileStatus.PENDING

    def test_resume_skips_moved(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "source"
            src.mkdir()

            f1 = src / "one.pdf"
            f2 = src / "two.pdf"
            f1.write_bytes(b"%PDF-1.4 fake")
            f2.write_bytes(b"%PDF-1.4 fake")

            dest = Path(d) / "dest"

            entry1 = FileEntry(
                original_name="one.pdf",
                source_path=f1,
                destination_path=dest / "Documents" / "one.pdf",
                category=Category.DOCUMENTS,
                status=FileStatus.MOVED,
            )
            entry2 = FileEntry(
                original_name="two.pdf",
                source_path=f2,
                destination_path=dest / "Documents" / "two.pdf",
                category=Category.DOCUMENTS,
                status=FileStatus.PENDING,
            )

            plan = Plan(source=src, destination=dest, entries=[entry1, entry2])
            executor = Executor(plan, simulate=False, resume=True)
            results = executor.run()

            # entry1 is skipped in resume mode (already moved)
            # only entry2 is processed
            assert len(results) == 1
            assert results[0].original_name == "two.pdf"
            assert results[0].status == FileStatus.MOVED

            # entry2 destination should exist
            assert (dest / "Documents" / "two.pdf").exists()
