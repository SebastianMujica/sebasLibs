# TODO — sebasLibs

## ✅ Completed (v0.1.0)

- [x] Project structure (pyproject.toml, git, README, .gitignore)
- [x] Core domain: entities, ports, event_bus
- [x] Classifier: extension + magic bytes, corruption detection
- [x] Planner: os.scandir, timeline (Year/Month), destination assignment
- [x] Executor: move, simulate, resume, collision handling
- [x] Adapters: fs_reader, fs_mover, csv_store, archiver, verifier, pillow_meta, progress_bar
- [x] Use cases: PlanUseCase, ExecuteUseCase
- [x] CLI entry point: `sebas-organize` (plan, execute, metadata, verify, extract-archives)
- [x] `execute` CLI: load plan CSV, run executor, save checkpoint, simulate/resume
- [x] `metadata` CLI: EXIF extraction pass, adjust subfolders by date_taken
- [x] Integration tests: plan->execute flow, simulate, resume
- [x] YAML rules: first-match-wins engine fully wired into plan
- [x] `--delete-after-archive` flag for extract-archives
- [x] Verify subcommand: zip report generation
- [x] `--hard-delete` support for rule delete action
- [x] Trash/ reversible delete implementation
- [x] Rule actions: skip, rename (regex capture groups), tag, delete
- [x] Planner respects rule-set subfolder and destination (no override)
- [x] Per-category CSV summary generation (summary_plan.txt with stats)
- [x] Weekly subdivision (Week 23 2024) when exceeding max-per-folder
- [x] Letter subdivision when exceeding max-per-folder
- [x] 7z/RAR optional support with graceful degradation (py7zr, rarfile)
- [x] Rules.yaml example with real-world use cases
- [x] Progress bar / TUI for large operations (rich or plain text fallback)
- [x] EXIF date override for timeline subfolder adjustment (--use-exif-date)
- [x] Full documentation (README.md with all commands, flags, rules, examples)
- [x] Tested on real folder: /mnt/e/Pictures (56 files, 327.9 MB)
- [x] Tests: 50 passing
- [x] Lint: ruff clean
- [x] Git remote: https://github.com/SebastianMujica/sebasLibs.git

## 🚧 In Progress

- [ ] Review CSV classification results from /mnt/e/Pictures test
- [ ] Execute real move (after CSV review approval)

## 🔜 Next Up

- [ ] Execute real move on /mnt/e/Pictures (pending CSV review)
- [ ] Cross-platform path handling (Windows drive letters, UNC paths)

## 📋 Backlog

- [ ] Dedupe tool (hash-based duplicate detection)
- [ ] CI/CD pipeline (GitHub Actions: lint + test)
- [ ] Type checking (mypy strict mode)

---

## 📌 Session Notes

### Real Folder Test: /mnt/e/Pictures
- **Date:** 2025-09-02
- **Files:** 56 total (327.9 MB)
  - Photos: 35 files (24.1 MB) → organized by Year/Month
  - Documents: 11 files (3.1 MB)
  - Archives: 4 files (206.6 MB)
  - Videos: 3 files (13.5 MB)
  - Others: 3 files (80.6 MB)
- **CSV files** copied to Windows desktop for review
- **Status:** Plan generated, execute simulated (no moves yet)
- **Next:** Review CSV → approve → execute real move
