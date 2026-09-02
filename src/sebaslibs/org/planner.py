"""Planner: scans a source directory, classifies files, and determines destinations."""

from __future__ import annotations

import calendar
import os
from datetime import datetime
from pathlib import Path

from ..core.entities import Category, FileEntry, Plan
from .classifier import classify_file
from .rule_engine import RuleEngine


class Planner:
    def __init__(
        self,
        source: Path,
        destination: Path,
        max_per_folder: int = 500,
        rules_engine: RuleEngine | None = None,
    ) -> None:
        self.source = source
        self.destination = destination
        self.max_per_folder = max_per_folder
        self.rules_engine = rules_engine

    def scan(self) -> Plan:
        """Scan source directory and return a plan with all files classified."""
        plan = Plan(source=self.source, destination=self.destination, max_per_folder=self.max_per_folder)
        entries: list[FileEntry] = []

        with os.scandir(self.source) as it:
            for entry in it:
                if entry.is_file(follow_symlinks=False):
                    file_path = Path(entry.path)
                    stat = entry.stat()
                    fe = FileEntry(
                        original_name=entry.name,
                        source_path=file_path,
                        size_bytes=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                        created=datetime.fromtimestamp(stat.st_ctime),
                    )

                    # Apply rules first (first match wins)
                    if self.rules_engine:
                        self.rules_engine.evaluate(fe)

                    # Default classification
                    classify_file(fe)

                    # Determine destination
                    self._assign_destination(fe)
                    entries.append(fe)

        plan.entries = entries
        return plan

    def _assign_destination(self, entry: FileEntry) -> None:
        """Build the destination path based on category and timeline."""
        # If rules already set a destination, respect it
        if entry.destination_path:
            return

        parts: list[str] = []

        # Category-based base folder
        if entry.category:
            parts.append(entry.category.value)
        else:
            parts.append(Category.OTHERS.value)

        # If rules already set a subfolder, use it
        if entry.subfolder:
            parts.append(entry.subfolder)
        # Timeline subfolder for Photos
        elif entry.category == Category.PHOTOS:
            timeline = self._build_timeline(entry)
            if timeline:
                parts.append(timeline)
        elif entry.category == Category.VIDEOS:
            timeline = self._build_timeline(entry)
            if timeline:
                parts.append(timeline)
        elif entry.category == Category.CORRUPTED:
            parts.append(entry.corruption_reason or "unknown")

        dest = self.destination / Path(*parts)
        entry.destination_path = dest / entry.original_name
        entry.subfolder = "/".join(parts[1:]) if len(parts) > 1 else entry.subfolder

    def _build_timeline(self, entry: FileEntry) -> str | None:
        """Build human-friendly timeline: Year/Month or Year/Week##."""
        ref_date = entry.date_taken or entry.modified
        if not ref_date:
            return None

        year = ref_date.year
        month_name = calendar.month_name[ref_date.month]  # e.g. "June"
        timeline = f"{year}/{month_name}"

        # If we need subdivide by week or letter when exceeding max_per_folder
        # This is handled at execution time when we count files per folder
        return timeline
