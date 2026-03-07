from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    EXHIBITS = "Exhibits"
    KEY_DOCUMENTS = "Key Documents"
    OTHER_DOCUMENTS = "Other Documents"
    TRANSCRIPTS = "Transcripts"
    RECORDINGS = "Recordings"

class ParsedEmailRequest(BaseModel):
    matter_number: str = Field(..., min_length=1)
    document_type: DocumentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    strategy: str  # "regex" or "llm"