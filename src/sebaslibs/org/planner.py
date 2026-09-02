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

        # Apply max-per-folder subdivision after initial assignment
        self._apply_max_per_folder(plan)

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
        """Build human-friendly timeline: Year/Month."""
        ref_date = entry.date_taken or entry.modified
        if not ref_date:
            return None

        year = ref_date.year
        month_name = calendar.month_name[ref_date.month]
        return f"{year}/{month_name}"

    def _apply_max_per_folder(self, plan: Plan) -> None:
        """Subdivide folders that exceed max_per_folder.

        Strategy:
        1. Week subdivision: "2024/June/Week 23 2024"
        2. Letter subdivision: "2024/June/A", "2024/June/B", etc.
        """
        # Group entries by their base folder (category + timeline)
        folder_groups: dict[str, list[FileEntry]] = {}
        for entry in plan.entries:
            if not entry.destination_path or entry.metadata.get("action") == "skip":
                continue
            base = entry.destination_path.parent
            folder_groups.setdefault(str(base), []).append(entry)

        for folder_path, entries in folder_groups.items():
            if len(entries) <= plan.max_per_folder:
                continue

            # Try week subdivision first
            if self._subdivide_by_week(entries, Path(folder_path)):
                continue
            # Fall back to letter subdivision
            self._subdivide_by_letter(entries, Path(folder_path))

    def _subdivide_by_week(self, entries: list[FileEntry], base_path: Path) -> bool:
        """Subdivide entries into weekly folders. Returns True if successful."""
        week_groups: dict[str, list[FileEntry]] = {}

        for entry in entries:
            ref_date = entry.date_taken or entry.modified
            if ref_date:
                iso_year, iso_week, _ = ref_date.isocalendar()
                week_key = f"Week {iso_week} {iso_year}"
                week_groups.setdefault(week_key, []).append(entry)
            else:
                week_groups.setdefault("Undated", []).append(entry)

        # Check if any week group still exceeds max
        for week_entries in week_groups.values():
            if len(week_entries) > self.max_per_folder:
                return False  # Week subdivision not sufficient

        # Apply week subdivision
        for week_key, week_entries in week_groups.items():
            for entry in week_entries:
                current_sub = entry.subfolder or ""
                new_sub = f"{current_sub}/{week_key}" if current_sub else week_key
                entry.subfolder = new_sub
                entry.destination_path = self.destination / new_sub / entry.original_name

        return True

    def _subdivide_by_letter(self, entries: list[FileEntry], base_path: Path) -> None:
        """Subdivide entries by first letter of filename."""
        letter_groups: dict[str, list[FileEntry]] = {}

        for entry in entries:
            letter = entry.original_name[0].upper() if entry.original_name else "0"
            if not letter.isalnum():
                letter = "0"
            letter_groups.setdefault(letter, []).append(entry)

        for letter, letter_entries in letter_groups.items():
            current_sub = letter_entries[0].subfolder or ""
            new_sub = f"{current_sub}/{letter}" if current_sub else letter
            for entry in letter_entries:
                entry.subfolder = new_sub
                entry.destination_path = self.destination / new_sub / entry.original_name
