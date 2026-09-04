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
    exec_parser.add_argument("--retry-errors", action="store_true", help="Also retry files with error status")

    # metadata
    meta_parser = subparsers.add_parser("metadata", help="Extract EXIF metadata from photos")
    meta_parser.add_argument("--plan-dir", required=True, help="Directory containing the plan CSV files")
    meta_parser.add_argument("--use-exif-date", action="store_true", help="Override timeline with EXIF date")

    # verify
    verify_parser = subparsers.add_parser("verify", help="Verify moved files")
    verify_parser.add_argument("--source", required=True, help="Directory to verify")
    verify_parser.add_argument("--zip", action="store_true", help="Create a zip report")

    # extract-archives
    extract_parser = subparsers.add_parser("extract-archives", help="Extract archives")
    extract_parser.add_argument("--source", required=True, help="Source directory")
    extract_parser.add_argument("--destination", help="Extraction destination")
    extract_parser.add_argument("--delete-after-archive", action="store_true", help="Delete original after extraction")

    # undo
    undo_parser = subparsers.add_parser("undo", help="Reverse a previous execute (move files back)")
    undo_parser.add_argument("--plan-dir", required=True, help="Directory containing the plan CSV files")
    undo_parser.add_argument("--simulate", action="store_true", help="Show what would happen without moving")
    undo_parser.add_argument("--include-errors", action="store_true", help="Also reset error entries to pending")

    # retry
    retry_parser = subparsers.add_parser("retry", help="Retry files that failed during execute")
    retry_parser.add_argument(
        "--plan-dir", required=True, help="Directory containing the plan CSV files",
    )
    retry_parser.add_argument("--simulate", action="store_true", help="Show what would happen")
    retry_parser.add_argument("--hard-delete", action="store_true", help="Permanently delete files")

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
    elif args.command == "undo":
        _run_undo(args)
    elif args.command == "retry":
        _run_retry(args)


def _run_plan(args: argparse.Namespace) -> None:
    from ...adapters.csv_store import CsvStore
    from ...adapters.progress_bar import ProgressHelper
    from ...org.use_cases import PlanUseCase

    source = Path(args.source).resolve()
    destination = Path(args.destination).resolve() if args.destination else source / "_organizer"
    rules_path = Path(args.rules) if args.rules else None

    with ProgressHelper.create(description="Scanning files", total=None) as progress:
        use_case = PlanUseCase(
            source=source,
            destination=destination,
            max_per_folder=args.max_per_folder,
            rules_path=rules_path,
        )
        plan = use_case.execute()

    store = CsvStore()

    with ProgressHelper.create(description="Saving plan", total=len(plan.entries)) as progress:
        store.save_plan(plan, destination)
        progress.update(advance=len(plan.entries))

    print(f"Plan created: {len(plan.entries)} files found")
    print(f"  Categories: {_count_categories(plan.entries)}")
    print(f"Output: {destination}")


def _run_execute(args: argparse.Namespace) -> None:
    from ...adapters.csv_store import CsvStore
    from ...adapters.progress_bar import ProgressHelper
    from ...core.entities import FileStatus
    from ...org.use_cases import ExecuteUseCase

    plan_dir = Path(args.plan_dir).resolve()
    store = CsvStore()
    plan = store.load_plan(plan_dir)

    if plan is None:
        print(f"No plan found in {plan_dir}. Run 'plan' first.")
        sys.exit(1)

    # If --retry-errors, reset error entries to pending
    if args.retry_errors:
        for entry in plan.entries:
            if entry.status == FileStatus.ERROR:
                entry.status = FileStatus.PENDING
        count = sum(1 for e in plan.entries if e.status == FileStatus.PENDING)
        print(f"Reset {count} entries to pending (including errors)")

    print(f"Loaded plan: {plan.total_count} files, {plan.pending_count} pending")

    use_case = ExecuteUseCase(
        plan=plan,
        simulate=args.simulate,
        resume=args.resume,
        hard_delete=args.hard_delete,
    )

    with ProgressHelper.create(description="Executing plan", total=plan.pending_count) as progress:
        results = use_case.execute()
        for _ in results:
            progress.update()

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

    from ...adapters.csv_store import CsvStore
    from ...adapters.pillow_meta import PillowMetadataExtractor
    from ...adapters.progress_bar import ProgressHelper
    from ...core.entities import Category

    plan_dir = Path(args.plan_dir).resolve()
    store = CsvStore()
    extractor = PillowMetadataExtractor()

    plan = store.load_plan(plan_dir)
    if plan is None:
        print(f"No plan found in {plan_dir}. Run 'plan' first.")
        sys.exit(1)

    photo_entries = [e for e in plan.entries if e.category == Category.PHOTOS]

    with ProgressHelper.create(description="Extracting EXIF", total=len(photo_entries)) as progress:
        updated = 0
        for entry in photo_entries:
            exif = extractor.extract_exif(entry.source_path)
            if exif:
                if args.use_exif_date and "date_taken_parsed" in exif:
                    entry.date_taken = exif["date_taken_parsed"]
                    dt = entry.date_taken
                    entry.subfolder = f"{dt.year}/{calendar.month_name[dt.month]}"
                    entry.destination_path = plan.destination / entry.subfolder / entry.original_name
                    updated += 1
                elif "camera" in exif or "resolution" in exif:
                    if "camera" in exif:
                        entry.camera = exif["camera"]
                    if "resolution" in exif:
                        entry.resolution = exif["resolution"]
                    updated += 1
            progress.update()

    store.save_plan(plan, plan_dir)
    print(f"Updated {updated}/{len(photo_entries)} photos with EXIF data")


def _run_verify(args: argparse.Namespace) -> None:
    import zipfile
    from datetime import datetime

    from ...adapters.verifier import Verifier

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
    from ...adapters.archiver import ArchiveReader
    from ...adapters.progress_bar import ProgressHelper

    source = Path(args.source).resolve()
    destination = Path(args.destination).resolve() if args.destination else source / "_extracted"
    reader = ArchiveReader()

    archives = [item for item in source.iterdir() if item.is_file() and reader.is_archive(item)]

    with ProgressHelper.create(description="Extracting archives", total=len(archives)) as progress:
        for item in archives:
            if reader.has_password(item):
                print(f"Skipping encrypted: {item.name}")
                progress.update()
                continue
            extracted = reader.extract(item, destination)
            print(f"Extracted {len(extracted)} files from {item.name}")
            if args.delete_after_archive and extracted:
                item.unlink()
                print(f"Deleted original: {item.name}")
            progress.update()


def _count_categories(entries: list) -> dict:
    from collections import Counter
    cats = [e.category.value if e.category else "Unknown" for e in entries]
    return dict(Counter(cats))


def _run_undo(args: argparse.Namespace) -> None:
    from ...adapters.csv_store import CsvStore
    from ...adapters.progress_bar import ProgressHelper
    from ...core.entities import FileStatus

    plan_dir = Path(args.plan_dir).resolve()
    store = CsvStore()
    plan = store.load_plan(plan_dir)

    if plan is None:
        print(f"No plan found in {plan_dir}. Run 'plan' first.")
        sys.exit(1)

    # Only undo files that were moved
    entries_to_undo = [e for e in plan.entries if e.status == FileStatus.MOVED and e.destination_path]

    if args.include_errors:
        error_entries = [e for e in plan.entries if e.status == FileStatus.ERROR]
        entries_to_undo.extend(error_entries)

    if not entries_to_undo:
        print("No moved files to undo.")
        sys.exit(0)

    print(f"Undoing {len(entries_to_undo)} files...")

    success = 0
    errors = 0

    with ProgressHelper.create(description="Undoing moves", total=len(entries_to_undo)) as progress:
        for entry in entries_to_undo:
            if args.simulate:
                print(f"  Would move {entry.destination_path or '(error)'} → {entry.source_path}")
                success += 1
                progress.update()
                continue

            # For error entries, source may still exist
            if entry.destination_path and entry.destination_path.exists():
                try:
                    entry.source_path.parent.mkdir(parents=True, exist_ok=True)
                    entry.destination_path.rename(entry.source_path)
                    entry.status = FileStatus.PENDING
                    success += 1
                except Exception as e:
                    print(f"  Error moving {entry.original_name}: {e}")
                    errors += 1
            elif entry.status == FileStatus.ERROR:
                # Source still exists, just reset status
                entry.status = FileStatus.PENDING
                success += 1
            else:
                print(f"  Warning: {entry.destination_path} not found, skipping")
                errors += 1
            progress.update()

    if not args.simulate:
        store.save_plan(plan, plan_dir)
        store.save_checkpoint(plan, plan_dir)

    print(f"Undo complete: {success} restored, {errors} errors")
    if args.simulate:
        print("(simulate mode — no files were moved)")


def _run_retry(args: argparse.Namespace) -> None:
    from ...adapters.csv_store import CsvStore
    from ...adapters.progress_bar import ProgressHelper
    from ...core.entities import FileStatus
    from ...org.use_cases import ExecuteUseCase

    plan_dir = Path(args.plan_dir).resolve()
    store = CsvStore()
    plan = store.load_plan(plan_dir)

    if plan is None:
        print(f"No plan found in {plan_dir}. Run 'plan' first.")
        sys.exit(1)

    error_entries = [e for e in plan.entries if e.status == FileStatus.ERROR]

    if not error_entries:
        print("No error entries to retry.")
        sys.exit(0)

    print(f"Retrying {len(error_entries)} failed files...")

    # Reset errors to pending
    for entry in error_entries:
        entry.status = FileStatus.PENDING

    use_case = ExecuteUseCase(
        plan=plan,
        simulate=args.simulate,
        resume=False,
        hard_delete=args.hard_delete,
    )

    with ProgressHelper.create(description="Retrying errors", total=len(error_entries)) as progress:
        results = use_case.execute()
        for _ in results:
            progress.update()

    # Filter to only show retried entries
    retried = [r for r in results if r.status in (FileStatus.MOVED, FileStatus.ERROR)]
    moved = sum(1 for r in retried if r.status == FileStatus.MOVED)
    still_errors = sum(1 for r in retried if r.status == FileStatus.ERROR)

    if not args.simulate:
        store.save_plan(plan, plan_dir)
        store.save_checkpoint(plan, plan_dir)

    print(f"Retry results: {moved} fixed, {still_errors} still failing")
    if args.simulate:
        print("(simulate mode — no files were moved)")


if __name__ == "__main__":
    main()
