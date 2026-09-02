"""Tests for the organizer planner."""


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
