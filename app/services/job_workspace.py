from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from app.services.models import DocumentType


@dataclass(frozen=True)
class JobWorkspace:
    root_dir: Path
    downloads_dir: Path
    zip_path: Path


def create_job_workspace(
    *,
    base_dir: Path,
    task_id: str | None,
    matter_number: str,
    document_type: DocumentType,
) -> JobWorkspace:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    safe_task_id = task_id or "manual"
    slug = document_type.value.lower().replace(" ", "_")

    root_dir = base_dir / f"{ts}_{safe_task_id}_{matter_number}_{slug}"
    downloads_dir = root_dir / "downloads"
    zip_path = root_dir / f"{matter_number}_{slug}.zip"

    downloads_dir.mkdir(parents=True, exist_ok=True)

    return JobWorkspace(
        root_dir=root_dir,
        downloads_dir=downloads_dir,
        zip_path=zip_path,
    )