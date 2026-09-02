# TODO — sebasLibs

## ✅ Completed (v0.1.0)

- [x] Project structure (pyproject.toml, git, README, .gitignore)
- [x] Core domain: entities, ports, event_bus
- [x] Classifier: extension + magic bytes, corruption detection
- [x] Planner: os.scandir, timeline (Year/Month), destination assignment
- [x] Executor: move, simulate, resume, collision handling
- [x] Adapters: fs_reader, fs_mover, csv_store, archiver, verifier, pillow_meta
- [x] Use cases: PlanUseCase, ExecuteUseCase
- [x] CLI entry point: `sebas-organize` (plan, execute, metadata, verify, extract-archives)
- [x] `execute` CLI: load plan CSV, run executor, save checkpoint, simulate/resume
- [x] `metadata` CLI: EXIF extraction pass, adjust subfolders by date_taken
- [x] Integration tests: plan->execute flow, simulate, resume
- [x] Tests: 20 passing
- [x] Lint: ruff clean
- [x] Git remote: https://github.com/SebastianMujica/sebasLibs.git

## 🚧 In Progress

(none — ready for next iteration)

## 🔜 Next Up

- [ ] Activate YAML rules (first-match-wins engine fully wired into plan)
- [ ] `--delete-after-archive` flag for extract-archives
- [ ] Verify subcommand: zip report generation
- [ ] Per-category CSV summary generation in plan
- [ ] `--hard-delete` support for rule delete action
- [ ] Trash/ reversible delete implementation

## 📋 Backlog

- [ ] Dedupe tool (hash-based duplicate detection)
- [ ] 7z/RAR optional support with graceful degradation
- [ ] EXIF date override for timeline subfolder adjustment
- [ ] Progress bar / TUI for large operations
- [ ] Weekly subdivision (Week 23 2024) when exceeding max-per-folder
- [ ] Letter subdivision when exceeding max-per-folder
- [ ] Cross-platform path handling (Windows drive letters, UNC paths)
- [ ] CI/CD pipeline (GitHub Actions: lint + test)
- [ ] Type checking (mypy strict mode)
