"""Tests for the progress bar adapter."""

from sebaslibs.adapters.progress_bar import _HAS_RICH, ProgressHelper


class TestProgressHelper:
    def test_progress_bar_works(self, capsys):
        """Progress bar should complete successfully."""
        with ProgressHelper.create(description="Testing", total=10) as progress:
            for _ in range(10):
                progress.update()

        captured = capsys.readouterr()
        assert "Testing" in captured.out
        if not _HAS_RICH:
            assert "Done: 10 items processed" in captured.out
        else:
            # Rich outputs progress bar with percentage
            assert "0%" in captured.out or "100%" in captured.out

    def test_update_advances_counter(self):
        """Counter should advance with each update."""
        progress = ProgressHelper.create(description="Test", total=5)
        assert progress.current == 0
        progress.update()
        assert progress.current == 1
        progress.update(advance=3)
        assert progress.current == 4

    def test_context_manager(self):
        """Should enter and exit cleanly."""
        with ProgressHelper.create(description="Test", total=3) as progress:
            progress.update(advance=3)
        assert progress.current == 3

    def test_has_rich_flag(self):
        """Flag should correctly a boolean."""
        assert isinstance(_HAS_RICH, bool)
