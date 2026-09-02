"""CSV store adapter for plan persistence."""

from __future__ import annotations

import csv
from pathlib import Path

from ..core.entities import FileEntry, FileStatus, Plan
from ..core.ports import PlanStorePort

CSV_COLUMNS = [
    "original_name",
    "category",
    "subfolder",
    "source_path",
    "destination_path",
    "size_bytes",
    "modified",
    "created",
    "date_taken",
    "camera",
    "resolution",
    "status",
]


def _format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


class CsvStore(PlanStorePort):
    def __init__(self) -> None:
        self._index_file = "index.csv"
        self._checkpoint_file = "checkpoint.txt"

    def save_plan(self, plan: Plan, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        index_path = output_dir / self._index_file

        with open(index_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for entry in plan.entries:
                writer.writerow(self._entry_to_dict(entry))

        # Per-category CSV files
        categories: dict[str, list[FileEntry]] = {}
        for entry in plan.entries:
            cat = entry.category.value if entry.category else "Others"
            categories.setdefault(cat, []).append(entry)

        for cat_name, cat_entries in categories.items():
            cat_path = output_dir / f"{cat_name}.csv"
            with open(cat_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                for entry in cat_entries:
                    writer.writerow(self._entry_to_dict(entry))

        # Summary plan
        self._save_summary(plan, output_dir, categories)

    def _save_summary(self, plan: Plan, output_dir: Path, categories: dict[str, list[FileEntry]]) -> None:
        """Generate summary_plan.txt with statistics."""
        summary_path = output_dir / "summary_plan.txt"
        total_size = sum(e.size_bytes for e in plan.entries)

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("Plan Summary\n")
            f.write(f"{'=' * 50}\n")
            f.write(f"Source: {plan.source}\n")
            f.write(f"Destination: {plan.destination}\n")
            f.write(f"Max per folder: {plan.max_per_folder}\n")
            f.write(f"Total files: {plan.total_count}\n")
            f.write(f"Total size: {_format_size(total_size)}\n")
            f.write("\nCategories:\n")
            for cat_name in sorted(categories.keys()):
                cat_entries = categories[cat_name]
                cat_size = sum(e.size_bytes for e in cat_entries)
                f.write(f"  {cat_name}: {len(cat_entries)} files ({_format_size(cat_size)})\n")
            f.write("\nStatuses:\n")
            status_counts: dict[str, int] = {}
            for entry in plan.entries:
                status_counts[entry.status.value] = status_counts.get(entry.status.value, 0) + 1
            for status, count in sorted(status_counts.items()):
                f.write(f"  {status}: {count}\n")

    def load_plan(self, output_dir: Path) -> Plan | None:
        index_path = output_dir / self._index_file
        if not index_path.exists():
            return None

        entries: list[FileEntry] = []
        with open(index_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry = self._dict_to_entry(row)
                entries.append(entry)

        # Read source/dest from first entry or store separately
        source = Path(entries[0].source_path.parent) if entries else Path(".")
        destination = Path(entries[0].destination_path).parent if entries and entries[0].destination_path else Path(".")

        return Plan(source=source, destination=destination, entries=entries)

    def save_checkpoint(self, plan: Plan, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = output_dir / self._checkpoint_file
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            for entry in plan.entries:
                f.write(f"{entry.source_path}|{entry.status.value}\n")

    def load_checkpoint(self, output_dir: Path) -> Plan | None:
        checkpoint_path = output_dir / self._checkpoint_file
        if not checkpoint_path.exists():
            return None

        statuses: dict[str, str] = {}
        with open(checkpoint_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "|" in line:
                    path_str, status_str = line.rsplit("|", 1)
                    statuses[path_str] = status_str

        # We need a full plan to merge with, so this is partial
        return None

    def _entry_to_dict(self, entry: FileEntry) -> dict:
        return {
            "original_name": entry.original_name,
            "category": entry.category.value if entry.category else "",
            "subfolder": entry.subfolder or "",
            "source_path": str(entry.source_path),
            "destination_path": str(entry.destination_path) if entry.destination_path else "",
            "size_bytes": entry.size_bytes,
            "modified": entry.modified.isoformat() if entry.modified else "",
            "created": entry.created.isoformat() if entry.created else "",
            "date_taken": entry.date_taken.isoformat() if entry.date_taken else "",
            "camera": entry.camera or "",
            "resolution": entry.resolution or "",
            "status": entry.status.value,
        }

    def _dict_to_entry(self, row: dict) -> FileEntry:
        from datetime import datetime

        def _parse_dt(val: str) -> datetime | None:
            if val:
                try:
                    return datetime.fromisoformat(val)
                except ValueError:
                    pass
            return None

        from ..core.entities import Category

        cat_str = row.get("category", "")
        category = Category(cat_str) if cat_str and cat_str in Category._value2member_map_ else None

        return FileEntry(
            original_name=row.get("original_name", ""),
            source_path=Path(row.get("source_path", "")),
            destination_path=Path(row["destination_path"]) if row.get("destination_path") else None,
            category=category,
            subfolder=row.get("subfolder") or None,
            size_bytes=int(row.get("size_bytes", 0)),
            modified=_parse_dt(row.get("modified", "")),
            created=_parse_dt(row.get("created", "")),
            date_taken=_parse_dt(row.get("date_taken", "")),
            camera=row.get("camera") or None,
            resolution=row.get("resolution") or None,
            status=FileStatus(row.get("status", "pending")),
        )
