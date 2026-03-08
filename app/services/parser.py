from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, ValidationError

from app.core.errors import ParseError
from app.integrations.ollama_client import OllamaClient
from app.services.models import DocumentType, ParsedEmailRequest


# Matter number patterns:
# - matches things like "2024-123", "2024-00123", "M-12345", "Matter: 12345"
MATTER_PATTERNS = re.compile(r"\bM\d{5}\b", re.IGNORECASE)

DOC_TYPE_PATTERN: list[tuple[DocumentType, re.Pattern]] = [
    (
        DocumentType.EXHIBITS,
        re.compile(r"\bexhibit(s)?\b|\bexh\.?", re.IGNORECASE),
    ),
    (
        DocumentType.KEY_DOCUMENTS,
        re.compile(r"\bkey[-\s]?document(s)?\b|\bkey[-\s]?doc(s)?\b|\bkeydocs\b", re.IGNORECASE,),
    ),
    (
        DocumentType.OTHER_DOCUMENTS,
        re.compile(r"\bother[-\s]?document(s)?\b|\bother[-\s]?doc(s)?\b|\bmisc(\.|ellaneous)?\b", re.IGNORECASE,),
    ),
    (
        DocumentType.TRANSCRIPTS, 
        re.compile(r"\btranscript(s)?\b|\btrans\.?", re.IGNORECASE),
    ),
    (
        DocumentType.RECORDINGS,
        re.compile(r"\brecording(s)?\b|\baudio\b|\bvideo\b|\bzoom\b", re.IGNORECASE,),
    ),
]

# 2) doc type (first match wins; order matters if you have overlaps)
def _extract_doc_type_regex(text: str) -> Optional[DocumentType]:
    for doc_type, pat in DOC_TYPE_PATTERN:
        if pat.search(text):
            return doc_type
    return None


class _LLMExtraction(BaseModel):
    matter_number: str
    document_type: DocumentType
    confidence: float = 0.75


def parse_email_request(
    *,
    subject: str,
    body_plain: str,
    allowed_doc_types: list[DocumentType],
    ollama: Optional[OllamaClient] = None,
) -> ParsedEmailRequest:
    """
    Regex-first. If either field missing -> LLM fallback (if provided).
    """
    text = f"{subject}\n\n{body_plain}".strip()
    text = re.sub(r"\s+", " ", text)  # normalize whitespace

    matter = MATTER_PATTERNS.search(text)
    doc_type = _extract_doc_type_regex(text)

    if matter and doc_type and doc_type in allowed_doc_types:
        return ParsedEmailRequest(
            matter_number= matter.group(0).upper(),
            document_type=doc_type,
            confidence=0.95,
            strategy="regex",
        )
    
    return ParsedEmailRequest(
            matter_number='M11111',  # default to a dummy matter number to avoid issues downstream; we'll ask for clarification in the email reply
            document_type=DocumentType.OTHER_DOCUMENTS,  # default to a dummy doc type to avoid issues downstream; we'll ask for clarification in the email reply
            confidence=0.0,
            strategy="clarification_needed",
        )


    # LLM fallback only if needed + client provided (ONLY FOR LOCAL)
    if ollama is None:
        raise ParseError("Could not parse matter number and document type (no LLM fallback configured)")

    system = (
        "You extract structured fields from emails.\n"
        "Return ONLY valid JSON matching the schema.\n"
        f"Allowed document_type values: {[t.value for t in allowed_doc_types]}.\n"
    )

    prompt = (
        "Extract:\n"
        '1) "matter_number": the matter number identifier\n'
        '2) "document_type": one of the allowed values\n'
        '3) "confidence": 0..1\n\n'
        "Email text:\n"
        "-----\n"
        f"{text}\n"
        "-----\n"
    )

    raw = ollama.extract_json(prompt=prompt, system=system)

    try:
        parsed = _LLMExtraction.model_validate(raw)
    except ValidationError as e:
        return ParsedEmailRequest(
            matter_number='M11111',  # default to a dummy matter number to avoid issues downstream; we'll ask for clarification in the email reply
            document_type=DocumentType.OTHER_DOCUMENTS,  # default to a dummy doc type to avoid issues downstream; we'll ask for clarification in the email reply
            confidence=0.0,
            strategy="clarification_needed",
        )

    if parsed.document_type not in allowed_doc_types or not parsed.matter_number.strip():
        return ParsedEmailRequest(
            matter_number='M11111',  # default to a dummy matter number to avoid issues downstream; we'll ask for clarification in the email reply
            document_type=DocumentType.OTHER_DOCUMENTS,  # default to a dummy doc type to avoid issues downstream; we'll ask for clarification in the email reply
            confidence=0.0,
            strategy="clarification_needed",
        )

    return ParsedEmailRequest(
        matter_number=parsed.matter_number.strip(),
        document_type=parsed.document_type,
        confidence=float(parsed.confidence),
        strategy="llm",
    )







