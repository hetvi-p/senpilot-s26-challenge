from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.services.models import DocumentType


@dataclass(frozen=True)
class MatterCounts:
    exhibits: int
    key_documents: int
    other_documents: int
    transcripts: int
    recordings: int

    def get(self, doc_type: DocumentType) -> int:
        if doc_type == DocumentType.EXHIBITS:
            return self.exhibits
        if doc_type == DocumentType.KEY_DOCUMENTS:
            return self.key_documents
        if doc_type == DocumentType.OTHER_DOCUMENTS:
            return self.other_documents
        if doc_type == DocumentType.TRANSCRIPTS:
            return self.transcripts
        if doc_type == DocumentType.RECORDINGS:
            return self.recordings
        raise ValueError(f"Unknown doc type: {doc_type}")


@dataclass
class MatterOverview:
    matter_number: Optional[str] = None
    status: Optional[str] = None
    title_description: Optional[str] = None
    type_value: Optional[str] = None
    category_value: Optional[str] = None
    date_received: Optional[str] = None
    decision_date: Optional[str] = None
    outcome: Optional[str] = None
    counts: Optional[MatterCounts] = None


@dataclass(frozen=True)
class DownloadedDocument:
    saved_path: Path