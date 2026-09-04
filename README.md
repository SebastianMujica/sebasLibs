# sebasLibs

A personal utility library for file organization and more.

## Installation

```bash
pip install -e .              # Base installation
pip install -e ".[dev]"       # With dev tools (pytest, ruff)
pip install -e ".[tui]"       # With progress bar (rich)
```

## Quick Start

```bash
# 1. Scan a messy folder and create a plan
sebas-organize plan --source /path/to/messy/folder

# 2. Review the plan (CSV files in source/_organizer/)
# 3. Execute the plan (move files)
sebas-organize execute --plan-dir /path/to/messy/folder/_organizer

# 4. Verify everything moved correctly
sebas-organize verify --source /path/to/destination
```

## Commands

### `plan` — Scan and create an organization plan

Scans the source directory, classifies files, and writes a CSV plan. **Does not move any files.**

```bash
sebas-organize plan --source /path/to/folder \
    --destination /path/to/dest \
    --max-per-folder 500 \
    --rules /path/to/rules.yaml
```

| Flag | Default | Description |
|------|---------|-------------|
| `--source` | (required) | Directory to scan |
| `--destination` | `<source>/_organizer` | Where to save the plan CSV files |
| `--max-per-folder` | `500` | Max files per subfolder before subdivision |
| `--rules` | _(none)_ | Path to `rules.yaml` for custom rules |

**Outputs in `destination/`:**
- `index.csv` — All files with status `pending`
- `<Category>.csv` — Per-category breakdown (Documents.csv, Photos.csv, etc.)
- `summary_plan.txt` — Statistics (file count, size, categories)
- `checkpoint.txt` — For resume support

### `execute` — Execute a plan

Moves files according to the plan CSV. Updates status per row and saves checkpoint.

```bash
sebas-organize execute --plan-dir /path/to/plan_dir \
    --simulate \
    --resume \
    --hard-delete
```

| Flag | Default | Description |
|------|---------|-------------|
| `--plan-dir` | (required) | Directory containing plan CSV files |
| `--simulate` | `false` | Show what would happen without moving |
| `--resume` | `false` | Resume from checkpoint (skip already moved) |
| `--hard-delete` | `false` | Permanently delete files marked for deletion |

### `metadata` — Extract EXIF metadata from photos

Extracts date_taken, camera, resolution, GPS from photos and updates the plan.

```bash
sebas-organize metadata --plan-dir /path/to/plan_dir \
    --use-exif-date
```

| Flag | Default | Description |
|------|---------|-------------|
| `--plan-dir` | (required) | Directory containing plan CSV files |
| `--use-exif-date` | `false` | Override timeline with EXIF date_taken |

### `verify` — Verify moved files

Checks file integrity by comparing sizes and hashes.

```bash
sebas-organize verify --source /path/to/destination \
    --zip
```

| Flag | Default | Description |
|------|---------|-------------|
| `--source` | (required) | Directory to verify |
| `--zip` | `false` | Create a zip report with ok/corrupted structure |

### `extract-archives` — Extract archives

Extracts zip, tar, gz, bz2 archives (7z/rar with optional libs).

```bash
sebas-organize extract-archives --source /path/to/archives \
    --destination /path/to/extracted \
    --delete-after-archive
```

| Flag | Default | Description |
|------|---------|-------------|
| `--source` | (required) | Directory containing archives |
| `--destination` | `<source>/_extracted` | Where to extract files |
| `--delete-after-archive` | `false` | Delete original after successful extraction |

### `undo` — Reverse a previous execute

Moves files back from their organized location to their original location. Uses the CSV to track where each file came from.

```bash
sebas-organize undo --plan-dir /path/to/plan_dir \
    --simulate
```

| Flag | Default | Description |
|------|---------|-------------|
| `--plan-dir` | (required) | Directory containing the plan CSV files |
| `--simulate` | `false` | Preview what would be undone without moving |

Only reverses files with status `moved`. Files that failed or were skipped are left in place.

## Classification

Files are classified by **extension + magic bytes** into:

| Category | Extensions |
|----------|------------|
| Documents | pdf, doc, docx, txt, odt, rtf, xls, xlsx, ppt, pptx, csv, md |
| Photos | jpg, jpeg, png, gif, bmp, webp, tiff, tif, heic, heif, raw, cr2, nef |
| Videos | mp4, avi, mkv, mov, wmv, flv, webm, m4v |
| Music | mp3, flac, wav, ogg, aac, m4a, wma |
| Archives | zip, tar, gz, tgz, bz2, 7z, rar, xz |
| Corrupted | Zero-size files, invalid signatures |
| Others | Everything else |

## Timeline Structure

Photos and Videos are organized into human-friendly timelines:

```
Photos/
├── 2024/
│   ├── June/
│   │   ├── Week 23 2024/     # When exceeding max-per-folder
│   │   └── Week 24 2024/
│   └── July/
│       ├── A/                # Letter fallback when weeks aren't enough
│       └── B/
Videos/
└── 2024/
    └── August/
Documents/
└── ...
```

## Custom Rules (rules.yaml)

Rules are **declarative** and evaluated **before** the default classifier. **First match wins.**

```yaml
rules:
  # Skip hidden/system files
  - conditions:
      name_regex: "^\\."
    actions:
      skip: true

  # Move invoices to a specific subfolder
  - conditions:
      name_contains: "invoice"
    actions:
      move_to_category: Documents
      subfolder: invoices

  # Delete temp files (reversible, goes to Trash/)
  - conditions:
      extension: ".tmp"
    actions:
      delete: trash

  # Rename camera photos with date prefix
  - conditions:
      name_regex: "^(IMG|DSC)_?(\\d{8})\\."
    actions:
      rename: "photo_\\2.jpg"

  # Tag important contracts
  - conditions:
      name_contains: "contract"
      extension: ".pdf"
    actions:
      tag: ["important", "legal"]
```

### Conditions

`name`, `name_regex`, `name_contains`, `extension`, `base_category`,
`size_gte`, `size_lte`, `year`, `month`, `date_gte`, `date_lte`,
`is_archive`, `has_password`

### Actions

`move_to`, `move_to_category`, `subfolder`, `delete`, `rename` (with regex capture groups),
`skip`, `extract`, `tag`

## Archive Support

| Format | Support | Notes |
|--------|---------|-------|
| zip | ✅ Stdlib | Password detection, zip-slip protection |
| tar | ✅ Stdlib | |
| gz | ✅ Stdlib | |
| bz2 | ✅ Stdlib | |
| 7z | ⚠️ Optional | `pip install py7zr` |
| rar | ⚠️ Optional | `pip install rarfile` + `unrar` |

**Never extracted:** `.iso`, `.exe`, `.dmg`, `.deb`, `.img`, `.bin`

## Status Values

| Status | Description |
|--------|-------------|
| `pending` | Not yet processed |
| `processing` | Currently being moved |
| `moved` | Successfully moved |
| `corrupted` | Zero-size or invalid signature |
| `error` | Failed to move |
| `encrypted` | Archive with password (not extracted) |
| `extracted` | Archive successfully extracted |

## Architecture

```
src/sebaslibs/
├── core/          # Shared domain: entities, ports, event_bus
├── org/           # Organizer feature: classifier, planner, executor, rules
├── adapters/      # I/O: fs, csv, exif, archives, verifier, progress
└── tools/         # CLI clients: organize (more tools coming)
```

Clean Architecture + OOP. No DI frameworks — manual dependency injection.

## Development

```bash
pip install -e ".[dev]"
ruff check .           # Lint
pytest -v              # Tests
```

## License

MIT
