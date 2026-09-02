"""Tests for the organizer planner."""

import os
from datetime import datetime

from sebaslibs.core.entities import Category, FileEntry, FileStatus, Plan
from sebaslibs.org.planner import Planner


class TestPlanner:
    def test_scan_creates_plan(self, sample_files):
        source = sample_files[0].parent
        dest = source / "_organizer"
        planner = Planner(source=source, destination=dest)
        plan = planner.scan()

        assert plan.total_count > 0
        assert plan.source == source
        assert plan.destination == dest

    def test_scan_classifies_files(self, sample_files):
        source = sample_files[0].parent
        dest = source / "_organizer"
        planner = Planner(source=source, destination=dest)
        plan = planner.scan()

        categories = {e.category for e in plan.entries if e.category}
        assert len(categories) > 1

    def test_empty_directory(self, empty_dir):
        planner = Planner(source=empty_dir, destination=empty_dir / "_organizer")
        plan = planner.scan()
        assert plan.total_count == 0

    def test_week_subdivision_when_exceeds_max(self, tmp_path):
        """When a month folder exceeds max_per_folder, subdivide by week."""
        src = tmp_path / "source"
        src.mkdir()

        # Create 600 files in June 2024, spread across weeks 22-26
        for i in range(600):
            f = src / f"photo_{i:04d}.jpg"
            f.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
            # Set mtime to spread across June 2024 (weeks 22-26)
            day = (i % 30) + 1
            timestamp = datetime(2024, 6, day, 12, 0, 0).timestamp()
            os.utime(f, (timestamp, timestamp))

        dest = tmp_path / "dest"
        planner = Planner(source=src, destination=dest, max_per_folder=500)
        plan = planner.scan()

        # Check that no folder has more than max_per_folder
        folder_counts: dict[str, int] = {}
        for entry in plan.entries:
            if entry.destination_path:
                key = str(entry.destination_path.parent)
                folder_counts[key] = folder_counts.get(key, 0) + 1

        assert all(count <= 500 for count in folder_counts.values()), f"Folder counts: {folder_counts}"

    def test_letter_subdivision_fallback(self, tmp_path):
        """When week subdivision still exceeds max, fall back to letter."""

        src = tmp_path / "source"
        src.mkdir()
        dest = tmp_path / "dest"
        entries = []

        # Create 2000 entries all with same date (same week)
        for i in range(2000):
            name = f"photo_{i:04d}.jpg"
            f = src / name
            f.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
            entry = FileEntry(
                original_name=name,
                source_path=f,
                category=Category.PHOTOS,
                status=FileStatus.PENDING,
                modified=datetime(2024, 6, 15),
            )
            entries.append(entry)

        plan = Plan(source=src, destination=dest, entries=entries, max_per_folder=500)
        planner = Planner(source=src, destination=dest, max_per_folder=500)
        planner._apply_max_per_folder(plan)

        # Check letter subdivision was applied
        folder_counts: dict[str, int] = {}
        for entry in plan.entries:
            if entry.destination_path:
                key = str(entry.destination_path.parent)
                folder_counts[key] = folder_counts.get(key, 0) + 1

        assert all(count <= 500 for count in folder_counts.values())
