from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def zip_files(*, files: list[Path], zip_path: Path) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as zf:
        for file_path in files:
            if file_path.exists() and file_path.is_file():
                zf.write(file_path, arcname=file_path.name)

    return zip_path