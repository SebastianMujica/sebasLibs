"""CLI entry point for sebas-organize."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="sebas-organize: classify and organize files")
    subparsers = parser.add_subparsers(dest="command")

    # plan
    plan_parser = subparsers.add_parser("plan", help="Scan and create an organization plan")
    plan_parser.add_argument("--source", required=True, help="Source directory to scan")
    plan_parser.add_argument("--destination", help="Destination directory (default: source/_organizer)")
    plan_parser.add_argument("--max-per-folder", type=int, default=500, help="Max files per subfolder")
    plan_parser.add_argument("--rules", help="Path to rules.yaml")

    # execute
    exec_parser = subparsers.add_parser("execute", help="Execute a plan")
    exec_parser.add_argument("--plan-dir", required=True, help="Directory containing the plan CSV files")
    exec_parser.add_argument("--simulate", action="store_true", help="Show what would happen without moving")
    exec_parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    exec_parser.add_argument("--hard-delete", action="store_true", help="Permanently delete instead of moving to trash")

    # metadata
    meta_parser = subparsers.add_parser("metadata", help="Extract EXIF metadata from photos")
    meta_parser.add_argument("--plan-dir", required=True, help="Directory containing the plan CSV files")

    # verify
    verify_parser = subparsers.add_parser("verify", help="Verify moved files")
    verify_parser.add_argument("--source", required=True, help="Directory to verify")
    verify_parser.add_argument("--zip", action="store_true", help="Create a zip report")

    # extract-archives
    extract_parser = subparsers.add_parser("extract-archives", help="Extract archives")
    extract_parser.add_argument("--source", required=True, help="Source directory")
    extract_parser.add_argument("--destination", help="Extraction destination")
    extract_parser.add_argument("--delete-after-archive", action="store_true", help="Delete original after extraction")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "plan":
        _run_plan(args)
    elif args.command == "execute":
        _run_execute(args)
    elif args.command == "metadata":
        _run_metadata(args)
    elif args.command == "verify":
        _run_verify(args)
    elif args.command == "extract-archives":
        _run_extract(args)


def _run_plan(args: argparse.Namespace) -> None:
    from ..adapters.csv_store import CsvStore
    from ..org.use_cases import PlanUseCase

    source = Path(args.source).resolve()
    destination = Path(args.destination).resolve() if args.destination else source / "_organizer"
    rules_path = Path(args.rules) if args.rules else None

    use_case = PlanUseCase(
        source=source,
        destination=destination,
        max_per_folder=args.max_per_folder,
        rules_path=rules_path,
    )
    plan = use_case.execute()

    store = CsvStore()
    store.save_plan(plan, destination)

    print(f"Plan created: {len(plan.entries)} files found")
    print(f"  Categories: {_count_categories(plan.entries)}")
    print(f"Output: {destination}")


def _run_execute(args: argparse.Namespace) -> None:
    from ..adapters.csv_store import CsvStore
    from ..org.use_cases import ExecuteUseCase

    plan_dir = Path(args.plan_dir).resolve()
    store = CsvStore()
    plan = store.load_plan(plan_dir)

    if plan is None:
        print(f"No plan found in {plan_dir}. Run 'plan' first.")
        sys.exit(1)

    print(f"Loaded plan: {plan.total_count} files, {plan.pending_count} pending")

    use_case = ExecuteUseCase(
        plan=plan,
        simulate=args.simulate,
        resume=args.resume,
        hard_delete=args.hard_delete,
    )
    results = use_case.execute()

    moved = sum(1 for r in results if r.status.value == "moved")
    errors = sum(1 for r in results if r.status.value == "error")
    skipped = sum(1 for r in results if r.status.value == "pending")

    if not args.simulate:
        store.save_checkpoint(plan, plan_dir)

    print(f"Results: {moved} moved, {errors} errors, {skipped} skipped")
    if args.simulate:
        print("(simulate mode — no files were moved)")


def _run_metadata(args: argparse.Namespace) -> None:
    import calendar
    from pathlib import Path

    from ..adapters.csv_store import CsvStore
    from ..adapters.pillow_meta import PillowMetadataExtractor
    from ..core.entities import Category

    plan_dir = Path(args.plan_dir).resolve()
    store = CsvStore()
    extractor = PillowMetadataExtractor()

    plan = store.load_plan(plan_dir)
    if plan is None:
        print(f"No plan found in {plan_dir}. Run 'plan' first.")
        sys.exit(1)

    photo_entries = [e for e in plan.entries if e.category == Category.PHOTOS]
    print(f"Extracting EXIF from {len(photo_entries)} photos...")

    updated = 0
    for entry in photo_entries:
        exif = extractor.extract_exif(entry.source_path)
        if not exif:
            continue

        if "date_taken_parsed" in exif:
            entry.date_taken = exif["date_taken_parsed"]
            dt = entry.date_taken
            entry.subfolder = f"{dt.year}/{calendar.month_name[dt.month]}"
            entry.destination_path = plan.destination / entry.subfolder / entry.original_name

        if "camera" in exif:
            entry.camera = exif["camera"]
        if "resolution" in exif:
            entry.resolution = exif["resolution"]

        updated += 1

    store.save_plan(plan, plan_dir)
    print(f"Updated {updated}/{len(photo_entries)} photos with EXIF data")


def _run_verify(args: argparse.Namespace) -> None:
    import zipfile
    from datetime import datetime

    from ..adapters.verifier import Verifier

    source = Path(args.source).resolve()
    verifier = Verifier()
    results = verifier.verify_directory(source)
    ok = sum(1 for v in results.values() if v == "ok")
    bad = sum(1 for v in results.values() if v == "corrupted")
    print(f"Verified {len(results)} files: {ok} OK, {bad} issues")

    if args.zip:
        report_name = f"verify_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        report_path = source / report_name
        with zipfile.ZipFile(report_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path, status in results.items():
                relative = Path(path).relative_to(source)
                zf.writestr(f"{status}/{relative!s}", "")
        print(f"Report saved to {report_path}")


def _run_extract(args: argparse.Namespace) -> None:
    from ..adapters.archiver import ArchiveReader

    source = Path(args.source).resolve()
    destination = Path(args.destination).resolve() if args.destination else source / "_extracted"
    reader = ArchiveReader()

    for item in source.iterdir():
        if item.is_file() and reader.is_archive(item):
            if reader.has_password(item):
                print(f"Skipping encrypted: {item.name}")
                continue
            extracted = reader.extract(item, destination)
            print(f"Extracted {len(extracted)} files from {item.name}")
            if args.delete_after_archive and extracted:
                item.unlink()
                print(f"Deleted original: {item.name}")


def _count_categories(entries: list) -> dict:
    from collections import Counter
    cats = [e.category.value if e.category else "Unknown" for e in entries]
    return dict(Counter(cats))


if __name__ == "__main__":
    main()
