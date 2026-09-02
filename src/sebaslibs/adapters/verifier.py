"""Verifier adapter: checks file integrity after moves."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


class Verifier:
    def verify_moved_file(self, source: Path, destination: Path) -> bool:
        """Verify a file was moved correctly by comparing size and hash."""
        if not destination.exists():
            return False
        if source.exists():
            src_stat = source.stat()
            dst_stat = destination.stat()
            if src_stat.st_size != dst_stat.st_size:
                return False
            return self._compare_hashes(source, destination)
        return True

    def verify_directory(self, path: Path) -> dict:
        """Scan a directory and return a summary of file health."""
        results: dict = {}
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file(follow_symlinks=False):
                    fp = Path(entry.path)
                    is_ok = self._check_file(fp)
                    results[str(fp)] = "ok" if is_ok else "corrupted"
        return results

    def _compare_hashes(self, source: Path, destination: Path) -> bool:
        src_hash = self._hash_file(source)
        dst_hash = self._hash_file(destination)
        return src_hash == dst_hash

    def _hash_file(self, path: Path, chunk_size: int = 8192) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()

    def _check_file(self, path: Path) -> bool:
        try:
            stat = path.stat()
            if stat.st_size == 0:
                return False
            with open(path, "rb") as f:
                f.read(1)
            return True
        except (OSError, PermissionError):
            return False
