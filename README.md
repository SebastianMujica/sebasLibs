# sebasLibs

A personal utility library for file organization and more.

## Quick start

```bash
# Install
pip install -e .

# Organize files
sebas-organize plan --source /path/to/messy/folder
sebas-organize execute
```

## Tools

- **organize** — Classify, plan, and move files into a clean timeline structure.
- *(dedupe — coming soon)*

## Architecture

Clean Architecture + OOP. Core domain is shared across all tools; each tool lives
in its own `org/` feature module with adapters for I/O.

See `DECISIONS.md` for the full design document.
