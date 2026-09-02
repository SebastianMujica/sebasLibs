"""Archive reader adapter with zip-slip protection."""

from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path

from ..core.ports import ArchiveReaderPort

SAFE_EXTS: set[str] = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".tar.gz", ".tar.bz2"}
NEVER_EXTRACT: set[str] = {".iso", ".exe", ".dmg", ".deb", ".img", ".bin"}

OPTIONAL_EXTS: dict[str, str] = {
    ".7z": "py7zr",
    ".rar": "rarfile (requires unrar)",
}

DEFAULT_MAX_SIZE = 500 * 1024 * 1024  # 500 MB


def _check_optional_lib(ext: str) -> tuple[bool, str]:
    """Check if optional archive library is available."""
    lib_name = OPTIONAL_EXTS.get(ext, "")
    if not lib_name:
        return False, f"Unsupported extension: {ext}"
    try:
        if ext == ".7z":
            import py7zr  # noqa: F401
            return True, ""
        elif ext == ".rar":
            import rarfile  # noqa: F401
            return True, ""
    except ImportError:
        return False, f"Optional library '{lib_name}' not installed. Run: pip install {lib_name.split()[0]}"
    return False, f"Unsupported extension: {ext}"


class ArchiveReader(ArchiveReaderPort):
    def is_archive(self, file_path: Path) -> bool:
        ext = file_path.suffix.lower()
        if ext in NEVER_EXTRACT:
            return False
        if ext in OPTIONAL_EXTS:
            available, _ = _check_optional_lib(ext)
            return available
        return ext in SAFE_EXTS or file_path.name.endswith((".tar.gz", ".tar.bz2"))

    def has_password(self, file_path: Path) -> bool:
        ext = file_path.suffix.lower()
        if ext == ".zip":
            try:
                with zipfile.ZipFile(file_path) as zf:
                    for info in zf.infolist():
                        if info.flag_bits & 0x1:
                            return True
            except (zipfile.BadZipFile, OSError):
                pass
            return False
        if ext == ".rar":
            try:
                import rarfile
                with rarfile.RarFile(file_path) as rf:
                    for info in rf.infolist():
                        if info.flags & 0x4:
                            return True
            except Exception:
                pass
            return False
        return False

    def extract(
        self,
        archive_path: Path,
        dest_dir: Path,
        max_size_bytes: int | None = None,
    ) -> list[Path]:
        max_size = max_size_bytes or DEFAULT_MAX_SIZE
        ext = archive_path.suffix.lower()
        name = archive_path.name.lower()

        if ext in NEVER_EXTRACT:
            return []

        extracted: list[Path] = []

        try:
            if ext == ".zip":
                extracted = self._extract_zip(archive_path, dest_dir, max_size)
            elif ext in (".tar",) or name.endswith((".tar.gz", ".tar.bz2")):
                extracted = self._extract_tar(archive_path, dest_dir, max_size)
            elif ext == ".gz":
                extracted = self._extract_gz(archive_path, dest_dir, max_size)
            elif ext == ".bz2":
                extracted = self._extract_bz2(archive_path, dest_dir, max_size)
            elif ext == ".7z":
                extracted = self._extract_7z(archive_path, dest_dir, max_size)
            elif ext == ".rar":
                extracted = self._extract_rar(archive_path, dest_dir, max_size)
        except Exception:
            return []

        return extracted

    def _extract_zip(self, archive_path: Path, dest_dir: Path, max_size: int) -> list[Path]:
        extracted: list[Path] = []
        with zipfile.ZipFile(archive_path) as zf:
            for info in zf.infolist():
                if info.flag_bits & 0x1:
                    continue
                # Zip-slip protection
                target = Path(dest_dir) / Path(info.filename)
                if not str(target.resolve()).startswith(str(dest_dir.resolve())):
                    continue
                if info.file_size > max_size:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                if not info.is_dir():
                    data = zf.read(info.filename)
                    target.write_bytes(data)
                    extracted.append(target)
        return extracted

    def _extract_tar(self, archive_path: Path, dest_dir: Path, max_size: int) -> list[Path]:
        extracted: list[Path] = []
        mode = "r:*" if archive_path.name.endswith(".gz") else "r:bz2" if archive_path.name.endswith(".bz2") else "r"
        with tarfile.open(archive_path, mode) as tf:
            for member in tf.getmembers():
                target = Path(dest_dir) / Path(member.name)
                if not str(target.resolve()).startswith(str(dest_dir.resolve())):
                    continue
                if member.size > max_size:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                if member.isfile():
                    f = tf.extractfile(member)
                    if f:
                        target.write_bytes(f.read())
                        extracted.append(target)
        return extracted

    def _extract_gz(self, archive_path: Path, dest_dir: Path, max_size: int) -> list[Path]:
        import gzip
        extracted: list[Path] = []
        target = dest_dir / archive_path.stem
        if str(target.resolve()).startswith(str(dest_dir.resolve())):
            with gzip.open(archive_path, "rb") as f_in:
                data = f_in.read(max_size)
                if len(data) > 0:
                    target.write_bytes(data)
                    extracted.append(target)
        return extracted

    def _extract_bz2(self, archive_path: Path, dest_dir: Path, max_size: int) -> list[Path]:
        import bz2
        extracted: list[Path] = []
        target = dest_dir / archive_path.stem
        if str(target.resolve()).startswith(str(dest_dir.resolve())):
            with bz2.open(archive_path, "rb") as f_in:
                data = f_in.read(max_size)
                if len(data) > 0:
                    target.write_bytes(data)
                    extracted.append(target)
        return extracted

    def _extract_7z(self, archive_path: Path, dest_dir: Path, max_size: int) -> list[Path]:
        """Extract 7z archive using py7zr (optional dependency)."""
        import py7zr
        extracted: list[Path] = []
        dest_dir.mkdir(parents=True, exist_ok=True)

        with py7zr.SevenZipFile(archive_path, mode="r") as z:
            for entry in z.list():
                if entry.filename.endswith("/"):
                    continue
                target = Path(dest_dir) / Path(entry.filename)
                if not str(target.resolve()).startswith(str(dest_dir.resolve())):
                    continue
                if entry.uncompressed > max_size:
                    continue
                extracted_files = z.extract(path=dest_dir, targets=[entry.filename])
                extracted.extend(extracted_files)

        return extracted

    def _extract_rar(self, archive_path: Path, dest_dir: Path, max_size: int) -> list[Path]:
        """Extract RAR archive using rarfile (optional dependency)."""
        import rarfile
        extracted: list[Path] = []
        dest_dir.mkdir(parents=True, exist_ok=True)

        with rarfile.RarFile(archive_path) as rf:
            for info in rf.infolist():
                if info.flags & 0x4:
                    continue  # Skip encrypted
                target = Path(dest_dir) / Path(info.filename)
                if not str(target.resolve()).startswith(str(dest_dir.resolve())):
                    continue
                if info.file_size > max_size:
                    continue
                if not info.isdir():
                    rf.extract(info, path=dest_dir)
                    extracted.append(target)

        return extracted
