"""Progress bar with graceful degradation (rich or plain text)."""

from __future__ import annotations

try:
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False


class ProgressHelper:
    """Provides a progress bar interface that works with or without rich."""

    def __init__(self, description: str = "Processing", total: int | None = None) -> None:
        self.description = description
        self.total = total
        self.current = 0
        self._rich_progress: object | None = None
        self._rich_task: object | None = None

    def __enter__(self) -> "ProgressHelper":
        if _HAS_RICH:
            self._rich_progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
            )
            self._rich_progress.__enter__()  # type: ignore
            self._rich_task = self._rich_progress.add_task(  # type: ignore
                self.description,
                total=self.total,
            )
        else:
            print(f"{self.description}...", flush=True)
        return self

    def __exit__(self, *args: object) -> None:
        if _HAS_RICH and self._rich_progress:
            self._rich_progress.__exit__(*args)  # type: ignore
        else:
            print(f"Done: {self.current} items processed.", flush=True)

    def update(self, advance: int = 1, refresh_text: str | None = None) -> None:
        self.current += advance
        if _HAS_RICH and self._rich_progress and self._rich_task:
            self._rich_progress.update(self._rich_task, advance=advance)  # type: ignore
            if refresh_text:
                self._rich_progress.update(self._rich_task, description=refresh_text)  # type: ignore

    @staticmethod
    def create(description: str = "Processing", total: int | None = None) -> "ProgressHelper":
        return ProgressHelper(description=description, total=total)
